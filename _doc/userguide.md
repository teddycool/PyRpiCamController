# PyRpiCam User Guide

**Table of Contents**
- [Quick Start Guide](#quick-start-guide)
- [Step 1: Powering On](#step-1-powering-on)
- [Step 2: WiFi Setup with Comitup](#step-2-wifi-setup-with-comitup)
- [Step 3: Accessing the Web Interface](#step-3-accessing-the-web-interface)
- [Step 4: Using the Settings Interface](#step-4-using-the-settings-interface)
- [Using the File Share](#using-the-file-share)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

Welcome to your PyRpiCam! This guide will help you get your camera system up and running quickly for time-lapse photography, remote monitoring, or automated image capture.

## Quick Start Guide
![Overview](pyrpicam-comic2.png)

### What You'll Need
- Your PyRpiCam device (Raspberry Pi with camera)
- Power cable
- WiFi network details (network name and password)
- Computer, smartphone, or tablet with web browser

### Setup Steps
1. **Power on** and wait for startup (2-3 minutes)
2. **Connect to WiFi** using Comitup
3. **Access the web interface** to configure settings
4. **Start taking pictures** automatically

## Step 1: Powering On

1. **Connect the power cable** to your PyRpiCam
2. **Wait 2-3 minutes** for the system to fully boot
3. **The system is ready** when you can see the WiFi setup network

*[Picture suggestion: Photo of PyRpiCam device with power cable connected]*

## Step 2: WiFi Setup with Comitup

Your PyRpiCam uses Comitup for easy WiFi configuration:

### Connect to Setup Network
1. **On your phone or computer**, look for WiFi networks
2. **Find and connect to**: `comitup-XXX` (where XXX is random numbers)
3. **No password required** - this is a temporary setup network

*[Picture suggestion: Screenshot of WiFi list on phone showing "comitup-XXX" network]*

### Configure Your Home WiFi
1. **Open your web browser** - you should be automatically redirected to the setup page
2. **If not redirected**, go to: `http://10.42.0.1`
3. **Select your home WiFi** from the list
4. **Enter your WiFi password**
5. **Click "Connect"**
6. **Wait for the connection** - the setup network will disappear when successful

*[Picture suggestion: Screenshot of Comitup web interface showing WiFi network selection]*

### Troubleshooting WiFi
- **Can't see comitup network**: Wait longer after power-on, or restart the device
- **Connection fails**: Double-check password, ensure 2.4GHz network
- **Setup network stays active**: Connection failed, try again with correct password

## Step 3: Accessing the Web Interface

Once connected to your home WiFi:

### Find Your Camera
**Option 1: Device hostname**
- Go to: `http://[device-id].local:5000`
- Replace `[device-id]` with the ID printed on your device

**Option 2: Router admin page**
- Check your router for connected devices
- Look for "PyRpiCam" or similar
- Use the IP address: `http://192.168.1.XXX:5000`

*[Picture suggestion: Screenshot of web browser address bar showing http://pycam-abc123.local:5000]*

## Step 4: Using the Settings Interface

The web interface provides a settings form to configure your camera:

*[Picture suggestion: Screenshot of the main settings interface showing the different sections]*

### Basic Settings

#### Camera Mode
- **Mode**: Choose "Cam" for photo capture or "Stream" for video streaming
- **Resolution**: Select image size (higher = larger files, more detail)
- **Time Slot**: How often to take photos (in seconds)

#### Photo Schedule
- **Time Schedule**: Set start and stop hours (e.g., 6 to 19 for daylight only)
- Use 24-hour format (0-23)

*[Picture suggestion: Screenshot of camera settings section showing mode, resolution, and timing options]*

### Image Publishing

Configure where your photos should be sent:

#### URL Publishing
- **Enable**: Check to activate web upload
- **Location**: Your server URL for receiving photos
- **API Key**: Your unique authentication key

#### File Publishing  
- **Enable**: Check to save photos locally
- **Location**: Local folder path (usually pre-configured)
- **Format**: Choose JPG or other formats

*[Picture suggestion: Screenshot of publishing settings showing URL and file options]*

### Advanced Settings

#### Motion Detection
- **Active**: Enable to only take photos when motion is detected
- **Motion Count**: Sensitivity setting (lower = more sensitive)
- **History**: Number of frames to compare for motion

#### Image Adjustments
- **Brightness**: Adjust exposure (-1.0 to 1.0)
- **Crop**: Enable to capture only part of the image
- **Crop coordinates**: Define the area to capture

*[Picture suggestion: Screenshot of advanced settings showing motion detection and image adjustment options]*

## Using the File Share

Access your photos directly from your computer:

### Connecting to the File Share
**Windows**: Open File Explorer, type `\\[device-id].local\FileShare`
**Mac**: In Finder, press Cmd+K, enter `smb://[device-id].local/FileShare`
**Linux**: Use `smb://[device-id].local/FileShare`

### What You'll Find
- **images/**: All captured photos organized by date
- **logs/**: System logs for troubleshooting

*[Picture suggestion: Screenshot of file explorer showing the FileShare folder structure with images and logs folders]*

## Common Tasks

### Starting Photo Capture
1. **Set camera mode** to "Cam"
2. **Configure time slot** (e.g., 60 for one photo per minute)
3. **Set active hours** (e.g., 6 to 18 for daylight)
4. **Enable publishing** to your preferred destination
5. **Save settings** - photos will start automatically

### Checking Recent Activity
- **View the logs folder** in the file share
- **Check your upload destination** for new photos
- **Monitor the logs** for any error messages

### Adjusting for Different Conditions
- **Too dark**: Increase brightness setting
- **Too bright**: Decrease brightness setting  
- **Wrong area**: Use crop settings to focus on specific region
- **Too many photos**: Increase time slot interval

## Troubleshooting

### Can't Connect to WiFi
- Ensure network is 2.4GHz (not 5GHz)
- Check password spelling carefully
- Try restarting the PyRpiCam and repeat setup

### Can't Access Web Interface
- Verify camera is connected to your network (check router)
- Try IP address instead of hostname
- Ensure you're on the same network as the camera

### Photos Not Being Taken
- Check that time slot is set correctly
- Verify current time is within active hours
- Review logs for error messages

### Photos Not Uploading
- Test your internet connection
- Verify URL and API key settings
- Check logs for upload error messages

### File Share Login Required (Anonymous Access Issues)
If you're suddenly prompted for a username/password when accessing the file share:

1. **SSH into your device** and run the fix script:

```bash
ssh pi@[device-id].local
cd PyRpiCamController/Services
chmod +x fix_samba_anonymous.sh
./fix_samba_anonymous.sh
```

2. **Alternative manual fix**:

```bash
sudo systemctl restart smbd
sudo systemctl restart nmbd
```

3. **If still not working, try a full reboot**:

```bash
sudo reboot
```

The file share is configured for anonymous access - no login should be required.

*[Picture suggestion: Screenshot of log file showing typical system messages and any error indicators]*

## Support

For technical issues:
1. **Check the log files** first for error messages
2. **Note any specific error codes** or messages
3. **Document your settings** when reporting issues

The PyRpiCam is designed to run automatically once configured. Set it up once, and it will continue capturing and uploading photos according to your schedule!