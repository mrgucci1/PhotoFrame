````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
````markdown
# Raspberry Pi Photo Frame

A digital photo frame application for Raspberry Pi that displays random photos from an API endpoint with location information overlay. Perfect for creating a dynamic photo display that updates automatically.

## Features

- 📸 Displays random photos from a remote API
- 🌍 Shows location information overlay
- 🔄 Automatic photo updates every minute
- 💾 Smart caching system (15 photos cached for smooth transitions)
- 🖥️ Full-screen display support
- 🔌 Works offline with cached photos when internet is unavailable
- ⚡ Optimized for Raspberry Pi Zero 2 W

## Prerequisites

- Raspberry Pi Zero 2 W with Raspberry Pi OS installed
- Internet connection configured
- SSH access or direct access to the Pi
- Display connected to the Pi

## Installation Steps

### 1. Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Required System Packages
```bash
# Install Python and pip if not already installed
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies for PIL/Pillow
sudo apt install libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff5 -y

# Install tkinter (usually included but just in case)
sudo apt install python3-tk -y

# Install fonts for location text
sudo apt install fonts-dejavu-core -y
```

### 3. Create Project Directory
```bash
mkdir ~/photo_frame
cd ~/photo_frame
```

### 4. Copy Files
Copy `photo_frame.py` and `requirements.txt` to the `~/photo_frame` directory.

### 5. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 6. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 7. Test the Application
```bash
python3 photo_frame.py
```

### 8. Set Up Display (if using headless)
If you're running headless and want to display on an attached screen:
```bash
# Enable X11 forwarding if using SSH
export DISPLAY=:0

# Or if using VNC, make sure VNC server is running
```

### 9. Create Startup Script (Optional)
Create a script to auto-start on boot:

```bash
# Create startup script
cat > ~/photo_frame/start_photo_frame.sh << 'EOF'
#!/bin/bash
cd /home/pi/photo_frame
source venv/bin/activate
export DISPLAY=:0
python3 photo_frame.py
EOF

chmod +x ~/photo_frame/start_photo_frame.sh
```

### 10. Auto-start on Boot (Optional)
Add to crontab for auto-start:
```bash
crontab -e
```
Add this line:
```
@reboot sleep 30 && /home/pi/photo_frame/start_photo_frame.sh
```

### 11. Performance Optimization for Pi Zero 2 W
For better performance on the Pi Zero 2 W:

```bash
# Increase GPU memory split
sudo raspi-config
# Go to Advanced Options > Memory Split > Set to 128

# Optional: Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable hciuart

# Add to /boot/config.txt for better performance
echo "gpu_mem=128" | sudo tee -a /boot/config.txt
echo "disable_overscan=1" | sudo tee -a /boot/config.txt
```

### 12. Full Screen Mode (Optional)
To run in full screen automatically, modify the startup script:

```bash
# Edit the startup script
nano ~/photo_frame/start_photo_frame.sh

# Add this line before python3 command:
# export DISPLAY=:0
# python3 photo_frame.py &
# sleep 2
# xdotool search --name "Photo Frame" windowstate --add FULLSCREEN
```

## Usage Notes

- Press `Escape` key to close the application
- The app will cache 15 photos for smooth transitions (15 minutes worth)
- If internet is lost, it will continue showing cached photos
- Location information is displayed in the bottom-right corner
- Photos update every minute
- Cache is filled in the background automatically

## Troubleshooting

### Common Issues

1. **Font errors**: Ensure `fonts-dejavu-core` is installed
2. **Display issues**: Make sure `DISPLAY=:0` is set
3. **No photos loading**: Check internet connectivity and API endpoint
4. **Performance issues**: Increase GPU memory split to 128MB
5. **Cache not working**: Check console output for API errors

### Monitoring
Check the console output for debugging information:
```bash
# Run with verbose output
python3 photo_frame.py

# Check system resources
htop
free -h
```

### API Endpoint Verification
Test the API manually:
```bash
curl -s "https://keatondalquist.com/api/random-photo-info" | jq
```

## Configuration Options

You can modify these settings in `photo_frame.py`:
- `UPDATE_INTERVAL`: Time between photo changes (milliseconds)
- `CACHE_SIZE`: Number of photos to cache (default: 15)
- `API_ENDPOINT`: Photo API endpoint
- Font sizes and positioning in the `add_location_text` method

## Power Management

For continuous operation:
```bash
# Disable screen blanking
sudo raspi-config
# Go to Advanced Options > Screen Blanking > Disable

# Or via command line:
echo "@xset s noblank" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@xset s off" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@xset -dpms" >> ~/.config/lxsession/LXDE-pi/autostart
```