import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from io import BytesIO
import threading
import queue
import time
import json
import gc
import psutil
import os

# --- Configuration ---
API_ENDPOINT = "https://keatondalquist.com/api/random-photo-info"
UPDATE_INTERVAL = 180000  # 3 minutes in milliseconds
CACHE_SIZE = 2  # Small cache for Pi Zero
PREFETCH_THRESHOLD = 1  # Start prefetching when cache has 1 or fewer photos
MAX_MEMORY_MB = 150  # Lower memory limit for Pi Zero

# --- API Photo Management ---
def get_random_photo_from_api():
    """Fetch a random photo from the API endpoint."""
    try:
        print("Fetching random photo from API...")
        response = requests.get(API_ENDPOINT, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if data and 'fullUrl' in data:
            img_response = requests.get(data['fullUrl'], timeout=15)
            img_response.raise_for_status()
            
            try:
                image = Image.open(BytesIO(img_response.content))
                image.load()
                    
            except Exception as img_error:
                print(f"Invalid image data: {img_error}")
                return None
            
            location = data.get('place', 'Unknown Location')
            location = location.replace('_', ' ').replace('-', ' ').title()
        else:
            print("Invalid API response format")
            return None
        
        print(f"Successfully fetched photo from API - Location: {location}")
        return {'image': image, 'location': location}
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching photo from API: {e}")
        return None
    except Exception as e:
        print(f"Error processing API response: {e}")
        return None

class PhotoCache:
    """Manages a cache of photos with memory management."""
    
    def __init__(self, cache_size=CACHE_SIZE):
        self.cache_size = cache_size
        self.photo_queue = queue.Queue(maxsize=cache_size)
        self.is_fetching = False
        self.fetch_thread = None
        self.stop_fetching = False
        
    def start_background_fetching(self):
        """Start background thread to keep cache filled."""
        if not self.fetch_thread or not self.fetch_thread.is_alive():
            self.stop_fetching = False
            self.fetch_thread = threading.Thread(target=self._background_fetch, daemon=True)
            self.fetch_thread.start()
    
    def stop_background_fetching(self):
        """Stop background fetching."""
        self.stop_fetching = True
    
    def get_memory_usage_mb(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def cleanup_cache(self):
        """Clear cache and force garbage collection."""
        print("Cleaning up cache due to high memory usage...")
        
        while not self.photo_queue.empty():
            try:
                photo_data = self.photo_queue.get_nowait()
                if photo_data and 'image' in photo_data:
                    photo_data['image'].close()
                    del photo_data['image']
            except queue.Empty:
                break
        
        gc.collect()
        
        print(f"Cache cleaned. Memory usage: {self.get_memory_usage_mb():.1f} MB")
    
    def _background_fetch(self):
        """Background thread function to fetch photos."""
        while not self.stop_fetching:
            try:
                memory_usage = self.get_memory_usage_mb()
                if memory_usage > MAX_MEMORY_MB:
                    self.cleanup_cache()
                    time.sleep(10)
                    continue
                
                if self.photo_queue.qsize() < self.cache_size:
                    photo_data = get_random_photo_from_api()
                    if photo_data:
                        if not self.photo_queue.full():
                            self.photo_queue.put(photo_data)
                            print(f"Cached photo. Queue size: {self.photo_queue.qsize()}, Memory: {memory_usage:.1f} MB")
                    else:
                        print("Failed to fetch photo for cache")
                        time.sleep(5)
                else:
                    time.sleep(30)
                    
            except Exception as e:
                print(f"Error in background fetch: {e}")
                time.sleep(5)
    
    def get_photo(self):
        """Get a photo from cache, or fetch immediately if cache is empty."""
        try:
            if not self.photo_queue.empty():
                photo_data = self.photo_queue.get_nowait()
                print(f"Retrieved cached photo. Queue size: {self.photo_queue.qsize()}")
                return photo_data
            else:
                print("Cache empty, fetching photo immediately")
                return get_random_photo_from_api()
        except queue.Empty:
            print("Cache empty, fetching photo immediately")
            return get_random_photo_from_api()

# --- Main Application ---
class PhotoFrame:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Frame")
        self.root.geometry("800x600")
        self.root.configure(bg='black')

        self.label = tk.Label(root, bg='black')
        self.label.pack(expand=True, fill='both')

        self.root.bind('<Escape>', lambda e: self.cleanup_and_exit())
        
        self.root.bind('<Configure>', self.on_window_resize)

        self.current_pil_image = None
        self.current_location = None
        self.resize_timer = None
        
        # Initialize photo cache
        self.photo_cache = PhotoCache()
        self.photo_cache.start_background_fetching()
        
        self.update_image()
        
        self.schedule_memory_check()
    
    def cleanup_and_exit(self):
        """Clean up resources before exiting."""
        print("Cleaning up before exit...")
        self.photo_cache.stop_background_fetching()
        
        # Close current image
        if self.current_pil_image:
            self.current_pil_image.close()
        
        self.root.destroy()
    
    def schedule_memory_check(self):
        """Schedule periodic memory monitoring."""
        memory_usage = self.photo_cache.get_memory_usage_mb()
        print(f"Memory check - Usage: {memory_usage:.1f} MB")
        
        if memory_usage > MAX_MEMORY_MB:
            gc.collect()
        
        self.root.after(300000, self.schedule_memory_check)
    
    def add_location_text(self, image, location_text):
        """Add location text to the bottom-right corner of the image."""
        img_with_text = None
        draw = None
        try:
            img_with_text = image.copy()
            draw = ImageDraw.Draw(img_with_text)
            
            # Use a simple, reliable font approach
            font = None
            try:
                font_size = max(16, min(32, image.width // 30))
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                    "/System/Library/Fonts/Arial.ttf"  # macOS fallback
                ]
                
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except (OSError, IOError):
                        continue
                        
                if not font:
                    font = ImageFont.load_default()
                    
            except Exception as font_error:
                print(f"Font loading error: {font_error}")
                font = None
            
            if font and location_text:
                try:
                    bbox = draw.textbbox((0, 0), location_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    padding = 15
                    x = max(0, image.width - text_width - padding)
                    y = max(0, image.height - text_height - padding)
                    
                    draw.text((x, y), location_text, fill=(255, 255, 255, 127), font=font)
                except Exception as text_error:
                    print(f"Text drawing error: {text_error}")
            
            return img_with_text
            
        except Exception as e:
            print(f"Error adding location text: {e}")
            # Clean up if we created a copy but failed
            if img_with_text and img_with_text != image:
                try:
                    img_with_text.close()
                except:
                    pass
            return image

    def on_window_resize(self, event):
        # Only respond to window resize events, not label resize events
        if event.widget == self.root and self.current_pil_image:
            # Cancel any pending resize timer
            if self.resize_timer:
                self.root.after_cancel(self.resize_timer)
            
            # Set a new timer to resize the image after a short delay
            self.resize_timer = self.root.after(100, self.resize_current_image)

    def resize_current_image(self):
        """Resize the current image to fit the window."""
        if not self.current_pil_image:
            return
            
        resized_image = None
        text_image = None
        try:
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Ensure minimum size
            if window_width < 100 or window_height < 100:
                return
            
            resized_image = self.current_pil_image.copy()
            resized_image.thumbnail((window_width, window_height), Image.Resampling.LANCZOS)
            
            if self.current_location:
                text_image = self.add_location_text(resized_image, self.current_location)
                if text_image != resized_image:
                    resized_image.close()  # Close the intermediate image
                    resized_image = text_image
            
            self.tk_image = ImageTk.PhotoImage(resized_image)
            self.label.config(image=self.tk_image)
            
        except Exception as e:
            print(f"Error resizing image: {e}")
        finally:
            # Clean up temporary images
            if resized_image:
                try:
                    resized_image.close()
                except:
                    pass

    def update_image(self):
        display_image = None
        text_image = None
        old_image = None
        try:
            # Store reference to old image for cleanup
            old_image = self.current_pil_image
            
            photo_data = self.photo_cache.get_photo()
            
            if photo_data and 'image' in photo_data:
                self.current_pil_image = photo_data['image']
                self.current_location = photo_data['location']
                print(f"Using photo with location: {self.current_location}")
                
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                
                display_image = self.current_pil_image.copy()
                display_image.thumbnail((window_width, window_height), Image.Resampling.LANCZOS)
                
                if self.current_location:
                    text_image = self.add_location_text(display_image, self.current_location)
                    if text_image != display_image:
                        display_image.close()  # Close intermediate image
                        display_image = text_image
                
                self.tk_image = ImageTk.PhotoImage(display_image)
                self.label.config(image=self.tk_image)
                
                # Clean up the old image after successful display
                if old_image:
                    try:
                        old_image.close()
                    except:
                        pass

            else:
                print("Failed to get photo from cache or API")

        except Exception as e:
            print(f"Error displaying image: {e}")
        finally:
            # Clean up temporary images
            if display_image:
                try:
                    display_image.close()
                except:
                    pass
        
        # Schedule next update
        try:
            self.root.after(UPDATE_INTERVAL, self.update_image)
        except tk.TclError:
            print("Window destroyed, stopping updates")

if __name__ == '__main__':
    try:
        root = tk.Tk()
        app = PhotoFrame(root)
        
        # Handle window close event
        root.protocol("WM_DELETE_WINDOW", app.cleanup_and_exit)
        
        print("Starting photo frame application...")
        root.mainloop()
        
    except KeyboardInterrupt:
        print("Keyboard interrupt received")
        if 'app' in locals():
            app.cleanup_and_exit()
    except Exception as e:
        print(f"Fatal error: {e}")
        if 'app' in locals():
            try:
                app.cleanup_and_exit()
            except:
                pass
    finally:
        print("Application terminated")