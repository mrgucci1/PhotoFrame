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
CACHE_SIZE = 10  
PREFETCH_THRESHOLD = 3  # Start prefetching when cache has 3 or fewer photos
MAX_MEMORY_MB = 200  # Maximum memory usage before cleanup (in MB)

# --- API Photo Management ---
def get_random_photo_from_api():
    """Fetch a random photo from the API endpoint."""
    try:
        print("Fetching random photo from API...")
        response = requests.get(API_ENDPOINT, timeout=10)
        response.raise_for_status()
        
        # Parse JSON response to get image URL and location
        data = response.json()
        
        if data and 'fullUrl' in data:
            img_response = requests.get(data['fullUrl'], timeout=10)
            img_response.raise_for_status()
            image = Image.open(BytesIO(img_response.content))
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
        self.previous_images = []
        
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
        
        # Close previous images
        for img in self.previous_images:
            if img:
                img.close()
        
        self.root.destroy()
    
    def schedule_memory_check(self):
        """Schedule periodic memory monitoring."""
        memory_usage = self.photo_cache.get_memory_usage_mb()
        print(f"Memory check - Usage: {memory_usage:.1f} MB")
        
        if memory_usage > MAX_MEMORY_MB:
            self.cleanup_old_images()
            gc.collect()
        
        self.root.after(300000, self.schedule_memory_check)
    
    def cleanup_old_images(self):
        """Clean up old PIL images."""
        print("Cleaning up old images...")
        for img in self.previous_images:
            if img:
                img.close()
        self.previous_images.clear()
        gc.collect()

    def add_location_text(self, image, location_text):
        """Add location text to the bottom-right corner of the image."""
        try:
            # Create a copy of the image to draw on
            img_with_text = image.copy()
            draw = ImageDraw.Draw(img_with_text)
            
            # Try to use a better font, fallback to default if not available
            try:
                # Adjust font size based on image size
                font_size = max(12, min(24, image.width // 40))
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except (OSError, IOError):
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
            
            if font:
                # Get text dimensions
                bbox = draw.textbbox((0, 0), location_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Position in bottom-right corner with padding
                padding = 10
                x = image.width - text_width - padding
                y = image.height - text_height - padding
                
                # Draw the text in white with 50% transparency (127 out of 255)
                draw.text((x, y), location_text, fill=(255, 255, 255, 127), font=font)
            
            return img_with_text
        except Exception as e:
            print(f"Error adding location text: {e}")
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
        if self.current_pil_image:
            try:
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                
                resized_image = self.current_pil_image.copy()
                resized_image.thumbnail((window_width, window_height), Image.Resampling.LANCZOS)
                
                if self.current_location:
                    resized_image = self.add_location_text(resized_image, self.current_location)
                
                self.tk_image = ImageTk.PhotoImage(resized_image)
                self.label.config(image=self.tk_image)
                
                resized_image.close()
                
            except Exception as e:
                print(f"Error resizing image: {e}")

    def update_image(self):
        if self.current_pil_image:
            self.previous_images.append(self.current_pil_image)
            if len(self.previous_images) > 3:
                old_img = self.previous_images.pop(0)
                if old_img:
                    old_img.close()
        
        photo_data = self.photo_cache.get_photo()
        
        if photo_data:
            self.current_pil_image = photo_data['image']
            self.current_location = photo_data['location']
            print(f"Using photo with location: {self.current_location}")
            
            try:
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                
                display_image = self.current_pil_image.copy()
                display_image.thumbnail((window_width, window_height), Image.Resampling.LANCZOS)
                
                if self.current_location:
                    display_image = self.add_location_text(display_image, self.current_location)
                
                self.tk_image = ImageTk.PhotoImage(display_image)
                self.label.config(image=self.tk_image)
                
                display_image.close()

            except Exception as e:
                print(f"Error displaying image: {e}")
        else:
            print("Failed to get photo from cache or API")

        self.root.after(UPDATE_INTERVAL, self.update_image)

if __name__ == '__main__':
    root = tk.Tk()
    app = PhotoFrame(root)
    
    # Handle window close event
    root.protocol("WM_DELETE_WINDOW", app.cleanup_and_exit)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.cleanup_and_exit()