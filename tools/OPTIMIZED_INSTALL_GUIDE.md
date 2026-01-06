# PyRpiCamController Installation Guide

This directory contains the streamlined installation script for PyRpiCamController.

## Overview

### `install-all-optimized.py` 
**Simple, reliable installer featuring:**
- ✅ **One-time installation** - Install once per Pi, no complexity
- ✅ **Batched operations** - Efficient package installation 
- ✅ **Progress tracking** - Clear status updates during installation
- ✅ **Better error handling** - Improved error messages and recovery
- ✅ **Automatic configuration** - Complete system setup in one go

## Installation Process

### Prerequisites
- Raspberry Pi with camera module (PiCam3 or PiCam3HQ recommended)
- Fresh Raspberry Pi OS (Bookworm) installation on USB stick or SD card
- Internet connection for downloading packages
- SSH access or direct terminal access

### Quick Installation

1. **Clone the project:**
```bash
git clone https://github.com/teddycool/PyRpiCamController.git /home/pi/PyRpiCamController
cd /home/pi/PyRpiCamController/tools
```

2. **Run the installer:**
```bash
sudo python3 install-all-optimized.py
```

3. **Wait for completion** (typically 15-30 minutes)
   - The installer will show progress with timestamps
   - System will automatically reboot at the end
   - After reboot, the camera service starts automatically

### What the installer does

1. **System Update** - Updates OS packages to latest versions
2. **Package Installation** - Installs all required Python packages and system dependencies
3. **Service Setup** - Configures and enables all system services:
   - `camcontroller.service` - Main camera application
   - `camcontroller-web.service` - Web interface 
   - `camcontroller-update.service` - OTA update daemon (if enabled)
4. **File Permissions** - Sets up proper permissions for shared folders
5. **WiFi Management** - Installs and configures ComitUp for WiFi management
6. **Hostname Setup** - Sets unique hostname based on Pi's CPU serial

### After Installation

**Services that will be running:**
- Camera controller at startup
- Web interface at `http://hostname.local:8080`
- Samba file sharing for easy file access
- WiFi management (ComitUp) for easy network setup

**File locations:**
- Application: `/home/pi/PyRpiCamController`
- Shared files: `/home/pi/shared/` (images, logs, etc.)
- Settings: `/home/pi/PyRpiCamController/Settings/user_settings.json`

### Installation Complete

When installation finishes successfully, you will see output similar to:

```
============================================================
INSTALLATION COMPLETED SUCCESSFULLY!
============================================================
Total time: 1200 seconds (20m 0s)
Hostname: <hostname>.local
Web interface: http://<hostname>.local:8080
Samba share: \\<hostname>.local\shared

Next steps:
1. Reboot to activate all services
2. Configure WiFi via ComitUp portal
3. Access web interface for camera settings
============================================================
```

**Important**: The hostname will be automatically set based on your Pi's CPU serial number for unique identification on the network.

## Troubleshooting

### Installation Issues
```bash
# Check system space
df -h

# Check memory usage  
free -h

# Check network connectivity
ping -c 3 archive.raspberrypi.org
```

### Service Issues
```bash
# Check camera service status
sudo systemctl status camcontroller.service

# Check web service status  
sudo systemctl status camcontroller-web.service

# View service logs
sudo journalctl -u camcontroller.service -f
```

### Permission Issues
```bash
# Fix shared folder permissions
sudo chmod 755 /home/pi/shared
sudo chown pi:pi /home/pi/shared -R
```

### Post-Installation Testing
```bash
# Test camera service
cd /home/pi/PyRpiCamController/tools
python3 test_camera_service.py

# Test web service
python3 test_web_service.py

# Test SMB sharing
python3 test_smb_service.py

# Complete system validation
bash validate_installation.sh
```

## Hardware Recommendations

### Optimal Setup:
- **USB 3.0 stick** instead of SD card (faster, more reliable)
- **Fast internet** for initial package downloads
- **Quality power supply** (especially important for Pi 3B+)
- **Class 10+ SD card** minimum if using SD storage

### Memory Requirements:
- **Minimum**: 1GB RAM (Pi 3B+, Pi 4)
- **Recommended**: 2GB+ RAM for better performance
- **Note**: Pi Zero models may need swap file adjustment (see documentation)

## Network Configuration

### WiFi Setup:
After installation, if WiFi isn't working:
1. Use a phone or other device
2. Look for AP-<hostname> WiFi network
3. Connect and follow ComitUp setup wizard to connect to your wifi

### Web-access:
- **Web Interface**: `http://hostname.local:8080` 
- **Video Stream**: `http://hostname.local:8081` (when streaming enabled)
- **File Share**: `\\hostname.local\shared` (Windows) or `smb://hostname.local/shared` (Linux/Mac)

## Security Notes

- Default installation creates open Samba shares for easy access
- Web interface has no authentication by default
- Consider network isolation for production deployments
- Change default passwords and enable authentication for external access

## Support

For issues or questions:
1. Check the main project documentation
2. Review service logs for error details
3. Use the included test scripts to diagnose issues
4. Check GitHub issues for similar problems
5. Raise new a issue if needed or contact the maintainer of the github repo