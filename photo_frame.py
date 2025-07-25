import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from io import BytesIO
import threading
import queue
import time
import json

# --- Configuration ---
API_ENDPOINT = "https://keatondalquist.com/api/random-photo-info"
UPDATE_INTERVAL = 60000  # 1 minute in milliseconds
CACHE_SIZE = 15  # Cache 15 photos (15 minutes worth)
PREFETCH_THRESHOLD = 5  # Start prefetching when cache has 5 or fewer photos

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
            # Fetch the actual image
            img_response = requests.get(data['fullUrl'], timeout=10)
            img_response.raise_for_status()
            image = Image.open(BytesIO(img_response.content))
            location = data.get('place', 'Unknown Location')
            
            # Format location nicely (replace underscores with spaces, title case)
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
    """Manages a cache of photos for smooth transitions and offline support."""
    
    def __init__(self, cache_size=CACHE_SIZE):
        self.cache_size = cache_size
        self.photo_queue = queue.Queue(maxsize=cache_size)
        self.is_fetching = False
        self.fetch_thread = None
        
    def start_background_fetching(self):
        """Start background thread to keep cache filled."""
        if not self.fetch_thread or not self.fetch_thread.is_alive():
            self.fetch_thread = threading.Thread(target=self._background_fetch, daemon=True)
            self.fetch_thread.start()
    
    def _background_fetch(self):
        """Background thread function to fetch photos."""
        while True:
            try:
                if self.photo_queue.qsize() < self.cache_size:
                    photo_data = get_random_photo_from_api()
                    if photo_data:
                        if not self.photo_queue.full():
                            self.photo_queue.put(photo_data)
                            print(f"Cached photo. Queue size: {self.photo_queue.qsize()}")
                    else:
                        print("Failed to fetch photo for cache")
                        time.sleep(5)  # Wait before retrying on failure
                else:
                    time.sleep(30)  # Wait when cache is full
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
        self.root.geometry("800x600")  # Set initial size
        self.root.configure(bg='black')

        self.label = tk.Label(root, bg='black')
        self.label.pack(expand=True, fill='both')

        # Close with the Escape key
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        
        # Bind resize event to update image when window is resized
        self.root.bind('<Configure>', self.on_window_resize)

        self.current_pil_image = None
        self.current_location = None
        self.resize_timer = None
        
        # Initialize photo cache
        self.photo_cache = PhotoCache()
        self.photo_cache.start_background_fetching()
        
        self.update_image()

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
                
                # Draw semi-transparent background for text
                bg_padding = 5
                draw.rectangle([
                    x - bg_padding, y - bg_padding,
                    x + text_width + bg_padding, y + text_height + bg_padding
                ], fill=(0, 0, 0, 128))
                
                # Draw the text in white
                draw.text((x, y), location_text, fill=(255, 255, 255), font=font)
            
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
                # Get current window size
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                
                # Make a copy of the original image and resize it
                resized_image = self.current_pil_image.copy()
                resized_image.thumbnail((window_width, window_height), Image.Resampling.LANCZOS)
                
                # Add location text if available
                if self.current_location:
                    resized_image = self.add_location_text(resized_image, self.current_location)
                
                self.tk_image = ImageTk.PhotoImage(resized_image)
                self.label.config(image=self.tk_image)
                
            except Exception as e:
                print(f"Error resizing image: {e}")

    def update_image(self):
        # Get photo from cache
        photo_data = self.photo_cache.get_photo()
        
        if photo_data:
            self.current_pil_image = photo_data['image']
            self.current_location = photo_data['location']
            print(f"Using photo with location: {self.current_location}")
            
            # Display the image
            try:
                # Get current window size
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                
                # Resize image to fit the window while maintaining aspect ratio
                display_image = self.current_pil_image.copy()
                display_image.thumbnail((window_width, window_height), Image.Resampling.LANCZOS)
                
                # Add location text
                if self.current_location:
                    display_image = self.add_location_text(display_image, self.current_location)
                
                self.tk_image = ImageTk.PhotoImage(display_image)
                self.label.config(image=self.tk_image)

            except Exception as e:
                print(f"Error displaying image: {e}")
        else:
            print("Failed to get photo from cache or API")

        # Schedule next update
        self.root.after(UPDATE_INTERVAL, self.update_image)

if __name__ == '__main__':
    root = tk.Tk()
    app = PhotoFrame(root)
    root.mainloop()