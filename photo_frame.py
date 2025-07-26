import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from io import BytesIO
import threading
import time
import gc
import psutil
import os

# --- Configuration ---
API_ENDPOINT = "https://keatondalquist.com/api/random-photo-info"
UPDATE_INTERVAL = 180000  # 3 minutes in milliseconds
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
        self.next_photo_data = None
        self.fetch_thread = None
        self.stop_fetching = False
        
        # Start background fetching for the first photo
        self.start_background_fetch()
        
        # Start the display cycle
        self.update_image()
        
        self.schedule_memory_check()
    
    def start_background_fetch(self):
        """Start background thread to fetch the next photo."""
        if not self.fetch_thread or not self.fetch_thread.is_alive():
            self.stop_fetching = False
            self.fetch_thread = threading.Thread(target=self._fetch_next_photo, daemon=True)
            self.fetch_thread.start()
    
    def _fetch_next_photo(self):
        """Background thread function to fetch the next photo."""
        while not self.stop_fetching:
            try:
                if not self.next_photo_data:
                    print("Fetching next photo in background...")
                    self.next_photo_data = get_random_photo_from_api()
                    if self.next_photo_data:
                        print("Next photo ready")
                    else:
                        print("Failed to fetch next photo, retrying in 5 seconds...")
                        time.sleep(5)
                        continue
                
                # Wait a bit before checking again
                time.sleep(10)
                    
            except Exception as e:
                print(f"Error in background fetch: {e}")
                time.sleep(5)
    
    def get_memory_usage_mb(self):
        """Get current memory usage in MB."""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0
    
    def cleanup_and_exit(self):
        """Clean up resources before exiting."""
        print("Cleaning up before exit...")
        self.stop_fetching = True
        
        # Close current image
        if self.current_pil_image:
            self.current_pil_image.close()
        
        # Close next photo if it exists
        if self.next_photo_data and 'image' in self.next_photo_data:
            self.next_photo_data['image'].close()
        
        self.root.destroy()
    
    def schedule_memory_check(self):
        """Schedule periodic memory monitoring."""
        memory_usage = self.get_memory_usage_mb()
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
            
            # Get the next photo (wait if not ready)
            photo_data = None
            if self.next_photo_data:
                photo_data = self.next_photo_data
                self.next_photo_data = None  # Clear it so background thread fetches next one
            else:
                print("Next photo not ready, fetching immediately...")
                photo_data = get_random_photo_from_api()
                if not photo_data:
                    print("Failed to fetch photo immediately, retrying...")
                    # Retry until we get a photo
                    while not photo_data and not self.stop_fetching:
                        time.sleep(2)
                        photo_data = get_random_photo_from_api()
            
            if photo_data and 'image' in photo_data:
                self.current_pil_image = photo_data['image']
                self.current_location = photo_data['location']
                print(f"Using photo with location: {self.current_location}")
                
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                
                # Ensure minimum window size
                if window_width < 100 or window_height < 100:
                    window_width, window_height = 800, 600
                
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
                print("Failed to get photo")

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