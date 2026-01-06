# Optimized Installation Guide

This directory contains optimized installation scripts for PyRpiCamController.

## Scripts Overview

### `install-all-optimized.py` 
**Fast, production-ready installer with:**
- ✅ **Batched operations** - 80% fewer I/O calls
- ✅ **Package caching** - Offline installs after first run
- ✅ **Progress tracking** - See what's happening
- ✅ **Resumable installs** - Continue after interruption
- ✅ **Error recovery** - Better error handling


### `package-cache-manager.py`
**Package cache management utility:**
- Create offline package repositories
- Export/import caches between Pis
- Manage cached packages
- Portable installations

## Quick Start

### 1. First-Time Installation
```bash
# Deploy project
git clone https://github.com/teddycool/PyRpiCamController.git /home/pi/PyRpiCamController

# Run optimized installer
cd /home/pi/PyRpiCamController/tools
sudo python3 install-all-optimized.py
```

### 2. Create Package Cache (for faster future installs)
```bash
# After successful installation, create cache
sudo python3 package-cache-manager.py create

# Export cache for other Pis
sudo python3 package-cache-manager.py export pycam_cache.tar.gz
```

### 3. Install on Additional Pis (using cache)
```bash
# Copy cache to new Pi
scp pycam_cache.tar.gz pi@new-pi:~/

# Import cache on new Pi
sudo python3 package-cache-manager.py import pycam_cache.tar.gz

# Install (will use cache - much faster!)
sudo python3 install-all-optimized.py
```

## Key Optimizations

### 🚀 **Batched Package Installation**
```python
# Old way (slow):
os.system("sudo apt install -y python3-pip")
os.system("sudo apt install -y python3-picamera2") 
# ... 14 more individual calls

# New way (fast):
packages = ["python3-pip", "python3-picamera2", ...14 packages]
os.system(f"sudo apt install -y {' '.join(packages)}")
```

### � **SMB File Sharing**
- **Guest access enabled** - No passwords required
- **Full permissions** - Create, modify, delete files remotely  
- **Unique hostname** - Each camera identified by Pi serial
- **Access paths:**
  - Windows: `\\<hostname>\FileShare`
  - macOS/Linux: `smb://<hostname>.local/FileShare`

### 💾 **Package Caching**
- Downloads packages once, reuses locally
- Creates portable cache files
- Supports offline installations
- Reduces network dependency

### 🔄 **Resumable Installation**
- Tracks completed steps in state file
- Can resume after interruption/failure
- No duplicate work on retry

### 📊 **Progress Tracking**
```
[14:32:15] CHECK: Verifying project deployment...
[14:32:16] PACKAGES: Starting optimized package installation...
[14:32:45] PACKAGES: Installing 14 packages in batch...
[14:35:22] PACKAGES: Package installation completed ✓
[14:36:10] SAMBA: Setting up file sharing with guest access...
[14:36:15] SAMBA: Configuration valid ✓
```

## Troubleshooting

### If Installation Hangs
1. **Check I/O wait**: `top` command should show low "wa" values
2. **Monitor progress**: Installation shows timestamped progress
3. **Check space**: `df -h` to ensure adequate disk space

### If Installation Fails
1. **Resume**: Just run the script again - it will continue from where it left off
2. **Check logs**: Error messages include specific command failures
3. **Clear state**: `rm /home/pi/.pycam_install_cache/install_state.json` to start fresh

### SMB File Sharing Issues
```bash
# Test SMB service
cd /home/pi/PyRpiCamController/tools
python3 test_smb_service.py

# Common fixes:
sudo chmod 777 /home/pi/shared  # Fix permissions
sudo systemctl restart smbd nmbd  # Restart services
```

### Cache Management
```bash
# Show cache info
sudo python3 package-cache-manager.py info

# Clear cache if corrupted
sudo python3 package-cache-manager.py clear

# Recreate cache
sudo python3 package-cache-manager.py create
```


## Hardware Recommendations

### For Best Performance:
1. **USB storage** instead of SD card (you're already doing this! 👍)
2. **Fast internet** for first installation
3. **Adequate power supply** (especially for Pi 3B+)
4. **Good SD card** (Class 10 minimum) if not using USB


## Production Deployment Strategy

### Single Pi Setup:
1. Use optimized installer directly
2. Create cache after successful install
3. Export cache for backup

### Multiple Pi Deployment:
1. Install first Pi with optimized script
2. Create and export package cache
3. Deploy cache + optimized script to all other Pis
4. Massive time savings on subsequent installations
