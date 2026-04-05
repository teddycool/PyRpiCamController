# Troubleshooting Guide

Common issues and solutions for PyRpiCamController installation and operation.

## Settings and Configuration

### Settings Not Applying

**Mode Changes (Cam ↔ Stream):**
- Apply **immediately** - no restart needed
- Camera controller monitors Mode setting in real-time
- Stream should start/stop within seconds of Mode change

**Other Settings:**
- Require service restart to apply changes
- Use "Apply Changes & Restart Service" button in web interface
- Camera quality, resolution, timing settings all need restart

**Restart from Web Interface:**
```bash
# From web GUI: click "Apply Changes & Restart Service" button
# Manual restart:
sudo systemctl restart camcontroller.service
```

### SMB/Samba File Sharing Issues

**Connection Refused or Timeout:**
```bash
# Check SMB service status
sudo systemctl status smbd nmbd

# Restart SMB services
sudo systemctl restart smbd nmbd

# Check if SMB ports are listening
sudo netstat -tlnp | grep :445
sudo netstat -tlnp | grep :139

# Test SMB configuration
testparm /etc/samba/smb.conf

# Check file permissions
ls -la /home/pi/shared/
```

**SMB Share Access:**
- Share name: `shared` (not `FileShare`)
- Access: `\\pi-hostname.local\shared` or `\\pi-ip-address\shared`
- Guest access enabled - no password required
- If connection fails, try IP address instead of hostname

## Installation Issues

### Package Installation Failures

If package manager locks appear during installation:
- The install script automatically waits for locks to clear
- Manually check: `sudo apt list --upgradable`
- Clear locks if needed: `sudo rm /var/lib/dpkg/lock*`

### USB Boot Issues

If the Pi does not boot from USB:
- **Pi 4/5**: Check USB boot is enabled in Pi config
- **Pi 3B+**: May require initial SD card setup to enable USB boot
- Verify USB drive compatibility (some drives not supported)
- Try different USB ports (USB 3.0 preferred on Pi 4/5)

## Service Issues

### CamController Service Won't Start

Check service logs:
```bash
sudo journalctl -u camcontroller.service -f
```

Check Python errors:
```bash
sudo systemctl status camcontroller.service
```

**Common Issues:**

1. **KeyError: 'Cam'** - Settings structure mismatch
   - Check that settings manager is working: `python3 -c "from Settings.settings_manager import settings_manager; print(settings_manager.get('Cam.resolution'))"`
   - Verify hwconfig.py exists and is readable

2. **AttributeError: 'PiCam3' object has no attribute '_cam'** - Camera initialization failed
   - Check camera connection: `libcamera-hello --list-cameras`
   - Verify camera is enabled in raspi-config
   - Check camera permissions

3. **Camera update failed** - Camera capture issues
   - Restart camera service: `sudo systemctl restart camcontroller.service`
   - Check camera hardware: `vcgencmd get_camera`

### Web Interface Service Issues

Check web service:
```bash
sudo systemctl status camcontroller-web.service
```

Check service logs for errors:
```bash
sudo journalctl -u camcontroller-web.service -f
```

**Common Issues:**

1. **Gunicorn not found**: If you see "Failed to locate executable /usr/bin/gunicorn":
   ```bash
   # Check where gunicorn is installed
   which gunicorn
   
   # If it's at /usr/local/bin/gunicorn, update service file:
   sudo sed -i 's|/usr/bin/gunicorn|/usr/local/bin/gunicorn|' /etc/systemd/system/camcontroller-web.service
   sudo systemctl daemon-reload
   sudo systemctl restart camcontroller-web.service
   ```

2. **Port 80 access denied**: The web interface runs on port 80 (requires root):
   ```bash
   # Check if port 80 is available
   sudo netstat -tulpn | grep :80
   ```

3. **Python path issues**: Ensure PYTHONPATH is set correctly:
   ```bash
   # The service should have PYTHONPATH=/home/pi/PyRpiCamController
   # Check service file: /etc/systemd/system/camcontroller-web.service
   ```

**Manual Web Interface Startup**:
If the service fails, you can start the web interface manually:
```bash
cd /home/pi/PyRpiCamController/WebGui
export PYTHONPATH=/home/pi/PyRpiCamController
python3 web_app.py
```

## Network Issues

### SMB Share Not Accessible

Check Samba service:
```bash
sudo systemctl status smbd.service
sudo systemctl status nmbd.service
```

Test SMB connectivity:
```bash
# Test from Pi itself
smbclient -L localhost -N

# Check share permissions
ls -la /home/pi/shared/
```

**SMB Access Methods:**
- **Windows**: Open File Explorer, navigate to `\\your-pi-ip\shared`
- **Mac**: Finder > Go > Connect to Server > `smb://your-pi-ip/shared`
- **Linux**: `smb://your-pi-ip/shared` in file manager

### WiFi Configuration Issues

If WiFi setup fails, the device should create an access point named `comitup-<number>`. Connect to that network and open the captive portal to configure WiFi.

Check comitup status:
```bash
sudo systemctl status comitup
sudo journalctl -u comitup -f
```

## Settings and Configuration Issues

### Settings Manager Not Working

Test settings system:
```bash
cd /home/pi/PyRpiCamController
python3 -c "from Settings.settings_manager import settings_manager; print(settings_manager.schema)"
```

### Hardware Configuration Issues

Check hwconfig.py:
```bash
cd /home/pi/PyRpiCamController/CamController
python3 -c "from hwconfig import hwconfig; print(hwconfig)"
```

### Web Interface Settings Not Saving

Check file permissions:
```bash
ls -la /home/pi/PyRpiCamController/Settings/
sudo chown -R pi:pi /home/pi/PyRpiCamController/Settings/
```

## Camera Issues

### Camera Not Detected

```bash
# Check camera detection
libcamera-hello --list-cameras

# Check camera in config
sudo raspi-config
# Navigate to Interface Options > Camera > Enable

# Check camera hardware
vcgencmd get_camera
```

### Image Capture Fails

```bash
# Test camera manually
libcamera-still -o test.jpg --width 1920 --height 1080

# Check permissions
sudo usermod -a -G video pi
```

## Log Analysis

### Main Service Logs

```bash
# Follow all camera controller logs
sudo journalctl -u camcontroller.service -f

# Get recent errors only
sudo journalctl -u camcontroller.service --since "1 hour ago" -p err

# Check specific component logs
sudo journalctl -u camcontroller.service | grep "cam.PiCam3"
```

### SMB Share Logs

```bash
cat /home/pi/shared/logs/cam.log | tail -50
```

### System Resource Issues

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU temperature
vcgencmd measure_temp
```

## Debugging Mode

Enable debug logging:
```bash
cd /home/pi/PyRpiCamController
# Edit settings to enable debug logging via web interface
# Or manually set logging level in settings
```

## Reset and Recovery

### Reset Settings to Default

```bash
cd /home/pi/PyRpiCamController/Settings
cp settings_schema.json user_settings.json.backup
rm -f user_settings.json
sudo systemctl restart camcontroller.service
```

### Complete System Reset

```bash
sudo systemctl stop camcontroller.service
sudo systemctl stop camcontroller-web.service
cd /home/pi/PyRpiCamController
git pull  # Get latest changes
python3 tools/install-all-optimized.py  # Reinstall
```

## Getting Help

When reporting issues, include:
1. Output of: `sudo systemctl status camcontroller.service`
2. Recent logs: `sudo journalctl -u camcontroller.service --since "1 hour ago"`
3. Hardware info: `cat /proc/cpuinfo | grep Model`
4. Camera status: `libcamera-hello --list-cameras`
5. Service status: `systemctl list-units | grep camcontroller`