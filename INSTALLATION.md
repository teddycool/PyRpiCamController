# Installation Guide

Complete installation instructions for PyRpiCamController on Raspberry Pi with USB boot.

## Current Scope

This guide covers camera runtime, web UI, SMB sharing, and WiFi setup.

OTA updates are **not supported yet** for production use. Some OTA-related files and services may exist in the repository, but they are not part of the supported installation flow.

## Prerequisites

**Hardware Requirements:**
- **Raspberry Pi**: 3B+, 4B, or 5 (has WiFi and is USB boot capable)
- **USB Drive**: SanDisk Ultra Fit 100GB+ recommended for system and image storage (USB 3.0+ for best performance)
- **Camera**: Raspberry Pi Camera Module 3 or HQ Camera
- **Power**: Sufficient power supply for your model

**Important**: Raspberry Pi Zero models, Raspberry Pi 2A/B, and 3A/3B are **not supported** in this guide because they cannot boot directly from USB. They may still work with SD-card boot and additional setup, but that is outside the scope of this document.

A circuit diagram for optional auxiliary hardware used by some features can be found here: [Circuit diagram](_doc/extra_hardware.pdf)

## Step 1: Prepare USB Drive and Start the Pi

**Create USB Boot Drive:**
1. Use Raspberry Pi Imager to create a USB boot drive with the latest Raspberry Pi OS Lite (64-bit recommended)
2. Enable USB boot in Pi settings during imaging:
   - Set username/password
   - Configure WiFi credentials  
   - Enable SSH with key or password
   - Set hostname (optional)

**USB Boot Setup:**
- **Pi 4/5**: Boot directly from USB drive (no SD card needed)
- **Pi 3B+**: May need one-time SD card setup to enable USB boot, then remove SD card

When the Pi starts, it automatically connects to WiFi and gets an IP address. If you set a hostname, it will be available on the network under that name.

**Performance Benefits of USB Boot:**
- 3-5x faster I/O compared to SD cards
- Better reliability for 24/7 operation
- Reduced wear on SD card slot
- Improved camera processing performance

## Step 2: Copy Files to Raspberry Pi

First clone this repository to your computer:

```bash
git clone https://github.com/teddycool/PyRpiCamController.git
```

Then copy these folders from the cloned repo to the Pi user's home directory (typically `/home/pi`).

* `/PyRpiCamController/` - Complete project directory containing:
  * `/CamController/` - Main camera controller code
  * `/Settings/` - Unified settings system 
  * `/WebGui/` - Web interface for configuration
  * `/tools/` - Installation scripts
  * `/Services/` - System service configuration files

## Step 3: Install Software

Now run the `tools/install-all-optimized.py` script on your Pi. It updates the OS and installs all required packages and services. This can take a while. At the end, the installer prints a summary and sets a new hostname based on the CPU serial.

```bash
cd /home/pi/PyRpiCamController
python3 tools/install-all-optimized.py
```

Since OTA is not supported yet, disable the update daemon if it gets installed:

```bash
sudo systemctl disable --now camcontroller-update.service 2>/dev/null || true
```

Then reboot once to ensure all services and hostname changes are active:

```bash
sudo reboot
```

If you update only service templates without a full reinstall, apply the web service template manually:

```bash
cd /home/pi/PyRpiCamController
sudo cp Services/camcontroller-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart camcontroller-web.service
```

**Installation Features:**
- Automatic package dependency management
- SMB server setup for network file sharing
- System service configuration  
- Directory structure creation
- Web interface deployment
- Package manager lock handling
- Web service binds to port 80 as user `pi` using systemd capability
- OTA components are not enabled/supported in this workflow

**SMB File Server Setup:**
The installer automatically configures a Samba (SMB) server for easy network access to images and logs:

```
Network Share: \\your-pi-ip\shared
Path Structure:
├── /home/pi/shared/
│   ├── images/          # Captured photos with metadata
│   └── logs/           # System and camera operation logs
```

**SMB Access Details:**
- **Guest Access**: No username/password required
- **Write Permission**: Full read/write access for all users
- **Cross-Platform**: Accessible from Windows, Mac, Linux, mobile devices
- **Auto-Discovery**: Should appear in network neighborhood

## Step 4: Configure Settings

After installation and reboot, configure the system on the running Raspberry Pi. The software uses a modern unified settings system with separation between hardware and dynamic settings:

* **Option 1 (Recommended)**: Use the web interface at `http://your-pi-ip` for all dynamic settings
* **Option 2**: SSH into the Pi and edit settings files in `/Settings/` directory for dynamic settings  
* **Option 3**: For hardware configuration (camera type, GPIO pins), SSH into the Pi and modify `/CamController/hwconfig.py`

**Configuration Steps:**
1. Access the web interface at `http://your-pi-ip` to configure camera settings, intervals, and logging
2. For hardware changes, SSH into the Pi: `ssh pi@your-pi-ip`
3. Edit hardware settings if needed: `nano /home/pi/PyRpiCamController/CamController/hwconfig.py`
4. Restart services after hardware changes: `sudo systemctl restart camcontroller.service`

**Essential Settings to Configure:**
- Camera resolution and quality settings
- Image format for all publishers (currently fixed to `jpg`)
- Capture intervals and scheduling
- Motion detection sensitivity
- Network and logging preferences

**Configuration Architecture:**
- **Dynamic Settings**: All runtime configurable settings (camera resolution, intervals, logging) via unified settings system
- **Hardware Settings**: Hardware-specific configuration (camera chip type, GPIO pins, board type) in `hwconfig.py`

## Step 5: Verify Installation

After reboot, the system will be accessible via its new hostname (based on CPU serial number):

```bash
# Check main camera service
sudo systemctl status camcontroller.service

# Check web interface service  
sudo systemctl status camcontroller-web.service

# Optional: confirm OTA daemon is disabled (current recommended state)
sudo systemctl status camcontroller-update.service

# View recent logs
journalctl -u camcontroller.service -f
```

Expected state:
- `camcontroller.service`: active
- `camcontroller-web.service`: active
- `camcontroller-update.service`: inactive/disabled

You can also check the log file via SMB share or locally:

```bash
cat /home/pi/shared/logs/cam.log
```

**Access Points:**
- **Web Interface**: `http://your-pi-ip` (configured settings, live stream)
- **SMB Share**: `\\your-pi-ip\shared` (images and logs)
- **SSH**: Direct terminal access for maintenance

## Hardware Configuration

For hardware-specific settings that can't be changed dynamically, edit `/CamController/hwconfig.py`:

```python
hwconfig = {
    "Version": 1, 
    "CamChip": "PiCam3",          # Camera type: "PiCam3" or "PiCamHQ"
    "RpiBoard": "Rpi3B+",         # Raspberry Pi board type
    "LightBox": True,             # Enable/disable light box functionality
    "Io": {
        "lightcontrolgpio": 12,    # GPIO pin for light control (PWM0)
        "displaycontrolgpio": 18,  # GPIO pin for display control (PWM0)
        "displaysize": 1,          # Number of LEDs
    },
}
```

**Supported Camera Types:**
- `"PiCam2"`: Raspberry Pi Camera Module 2
- `"PiCam3"`: Raspberry Pi Camera Module 3 (default)
- `"PiCamHQ"`: Raspberry Pi High Quality Camera
- `"WebCam"`: USB webcam fallback

**Note:** Hardware settings require restart to take effect, while dynamic settings (via web interface) are applied immediately.

## WiFi Management with Comitup

WiFi is handled by the Comitup software from Dave Steel. If no known network is found, the device starts an access point and allows you to configure a new WiFi connection through a web interface.

**Key Features:**
- Automatic fallback to access point mode if no known WiFi networks are found
- Easy WiFi configuration through captive portal web interface
- No need for keyboard/monitor attached to Raspberry Pi

For more information: https://github.com/davesteele/comitup/wiki/Installing-Comitup

## Troubleshooting

For detailed troubleshooting information, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

**Quick Checks:**
```bash
# Check both services are running
sudo systemctl status camcontroller.service
sudo systemctl status camcontroller-web.service

# OTA daemon should be disabled until OTA support is released
sudo systemctl is-enabled camcontroller-update.service

# View live logs
sudo journalctl -u camcontroller.service -f
```