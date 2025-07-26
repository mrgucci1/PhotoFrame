# Raspberry Pi Photo Frame

A simple, reliable digital photo frame application for Raspberry Pi that displays random photos from an API endpoint with location information overlay. Designed for stability and minimal resource usage.

## Features

- 📸 Displays random photos from a remote API
- 🌍 Shows location information overlay in bottom-right corner
- 🔄 Automatic photo updates every 3 minutes
- 🖥️ Full-screen display on startup
- ⚡ Optimized for Raspberry Pi Zero 2 W
- 🎯 Simple, crash-resistant design
- 🔌 Direct API fetching (no caching complexity)

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

### 3. Clone or Download the Project
```bash
# Option 1: Clone with git
git clone https://github.com/dalqu/PhotoFrame.git
cd PhotoFrame

# Option 2: Download as ZIP and extract
wget https://github.com/dalqu/PhotoFrame/archive/main.zip
unzip main.zip
cd PhotoFrame-main
```

### 4. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 6. Test the Application
```bash
python3 photo_frame.py
```

## Usage

### Controls
- **ESC key**: Exit the application
- **Application runs in fullscreen**: Automatically starts in fullscreen mode

### Behavior
- Photos update automatically every 3 minutes
- Location information is displayed in the bottom-right corner
- Application fetches photos directly from the API as needed
- If a photo fails to load, it will retry on the next cycle

## Auto-start on Boot (Optional)

### Create Startup Script
```bash
cat > ~/PhotoFrame/start_photo_frame.sh << 'EOF'
#!/bin/bash
sleep 30
cd /home/pi/PhotoFrame
source venv/bin/activate
export DISPLAY=:0
python3 photo_frame.py
EOF

chmod +x ~/PhotoFrame/start_photo_frame.sh
```

### Add to Crontab
```bash
crontab -e
```
Add this line:
```
@reboot /home/pi/PhotoFrame/start_photo_frame.sh
```

## Performance Optimization for Pi Zero 2 W

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

## Troubleshooting

### Common Issues

1. **No photos loading**: Check internet connectivity and API endpoint
2. **Display issues**: Make sure `DISPLAY=:0` is set when using SSH
3. **Font errors**: Ensure `fonts-dejavu-core` is installed
4. **Application won't start**: Check Python dependencies are installed

### Monitoring
Check the console output for debugging information:
```bash
python3 photo_frame.py
```

### API Endpoint Verification
Test the API manually:
```bash
curl -s "https://keatondalquist.com/api/random-photo-info" | jq
```

## Configuration Options

You can modify these settings in `photo_frame.py`:
- `UPDATE_INTERVAL`: Time between photo changes (default: 180000ms = 3 minutes)
- `API_ENDPOINT`: Photo API endpoint URL

## Technical Details

### Simplified Architecture
- **No caching**: Photos are fetched directly when needed
- **No threading**: All operations run in the main thread for stability
- **Minimal memory usage**: Only one photo in memory at a time
- **Error resilient**: Failures are logged and retried on next cycle

### Memory Usage
- Typical usage: 30-80MB RAM
- No memory leaks or accumulation
- Automatic cleanup of old images

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

## Files

- `photo_frame.py`: Main application file (~110 lines)
- `requirements.txt`: Python dependencies
- `README.md`: This documentation
