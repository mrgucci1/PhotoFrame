import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from io import BytesIO
import time
import gc
import os

# --- Configuration ---
API_ENDPOINT = "https://keatondalquist.com/api/random-photo-info"
UPDATE_INTERVAL = 180000  # 3 minutes in milliseconds

def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    mem_kb = int(line.split()[1])
                    return mem_kb / 1024  # Convert to MB
    except:
        pass
    return 0

def get_random_photo_from_api():
    """Fetch a random photo from the API endpoint."""
    try:
        print("Fetching photo from API...")
        response = requests.get(API_ENDPOINT, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data and 'fullUrl' in data:
            img_response = requests.get(data['fullUrl'], timeout=10)
            img_response.raise_for_status()
            
            image = Image.open(BytesIO(img_response.content))
            
            location = data.get('place', 'Unknown Location')
            location = location.replace('_', ' ').replace('-', ' ').title()
            
            print(f"Successfully fetched photo - Location: {location}")
            return {'image': image, 'location': location}
        
        return None
    
    except Exception as e:
        print(f"Error fetching photo: {e}")
        return None

class PhotoFrame:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Frame")
        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        
        self.label = tk.Label(root, bg='black')
        self.label.pack(expand=True, fill='both')

        self.current_image = None
        self.current_location = None
        self.image_count = 0
        
        # Start immediately
        self.update_image()
    
    def update_image(self):
        try:
            # Log memory usage before starting
            mem_before = get_memory_usage()
            print(f"Memory before update: {mem_before:.1f} MB")
            
            # Clean up old image
            if self.current_image:
                self.current_image.close()
                self.current_image = None
            
            # Force garbage collection
            gc.collect()
            
            # Get new photo
            photo_data = get_random_photo_from_api()
            
            if photo_data and 'image' in photo_data:
                self.current_image = photo_data['image']
                self.current_location = photo_data['location']
                self.image_count += 1
                
                # Log the new image with count and timestamp
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"Image #{self.image_count} - {current_time} - Location: {self.current_location}")
                
                # Get window size
                self.root.update_idletasks()
                width = self.root.winfo_width()
                height = self.root.winfo_height()
                
                if width < 100 or height < 100:
                    width, height = 800, 600
                
                # Resize original image to fit screen first
                self.current_image.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Now make a copy for adding text (smaller image now)
                display_image = self.current_image.copy()
                
                # Add location text
                if self.current_location:
                    try:
                        draw = ImageDraw.Draw(display_image)
                        font_size = max(20, width // 40)
                        
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
                        
                        # Simple text positioning
                        text = self.current_location
                        bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        x = display_image.width - text_width - 20
                        y = display_image.height - text_height - 20
                        
                        draw.text((x, y), text, fill=(255, 255, 255), font=font)
                    except Exception as e:
                        print(f"Text error: {e}")
                
                # Display
                self.tk_image = ImageTk.PhotoImage(display_image)
                self.label.config(image=self.tk_image)
                
                # Clean up
                display_image.close()
                
                # Log memory usage after
                mem_after = get_memory_usage()
                print(f"Memory after update: {mem_after:.1f} MB")
                
                # Warning if memory is getting high
                if mem_after > 200:
                    print(f"WARNING: High memory usage: {mem_after:.1f} MB")
                    gc.collect()  # Force garbage collection
                
                print("Photo displayed successfully")
            else:
                print("Failed to get photo")
        
        except Exception as e:
            print(f"Error in update_image: {e}")
            # Force cleanup on error
            gc.collect()
        
        # Schedule next update
        self.root.after(UPDATE_INTERVAL, self.update_image)

if __name__ == '__main__':
    print("Starting simple photo frame...")
    
    try:
        root = tk.Tk()
        app = PhotoFrame(root)
        root.mainloop()
    except Exception as e:
        print(f"Error: {e}")
    
    print("Photo frame closed")