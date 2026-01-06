# PyRpiCamController Test Scripts

This directory contains specialized test scripts for validating individual components of the PyRpiCamController system. Each script focuses on testing a specific service in isolation, making debugging and development much easier.

## Overview

The test scripts provide comprehensive testing for:
- **Camera Service** - Core camera functionality and streaming
- **Web Service** - Settings web interface and API
- **SMB Service** - File sharing and network access

All scripts follow the same pattern: setup, test, validate, and provide clear success/failure feedback.

---

## 📷 `test_camera_service.py`

**Purpose**: Tests the core camera controller service in isolation

### What it tests:
- ✅ Camera service installation and configuration
- ✅ Service startup and status checking
- ✅ Camera hardware detection
- ✅ Streaming functionality
- ✅ Settings file access
- ✅ Service restart capability

### Usage:
```bash
# Test camera service
python3 test_camera_service.py

# Stop camera service after testing  
python3 test_camera_service.py stop
```

### Key Features:
- **Isolated testing** - Only starts camcontroller.service
- **Hardware validation** - Detects camera modules
- **Service management** - Proper systemd integration
- **Error reporting** - Clear failure diagnostics
- **Clean shutdown** - Stops services when done

### Expected Output:
```
[CAM-TEST] === Camera Controller Service Test ===
[CAM-TEST] Configuring camera service...
[CAM-TEST] ✓ Service file created successfully
[CAM-TEST] ✓ Camera service started successfully  
[CAM-TEST] ✓ Camera service is running
[CAM-TEST] ✓ Camera hardware detected
[CAM-TEST] Camera service test PASSED
```

---

## 🌐 `test_web_service.py`

**Purpose**: Tests the web interface and settings management service

### What it tests:
- ✅ Web service installation and configuration
- ✅ Flask application startup
- ✅ Settings web interface accessibility
- ✅ API endpoint functionality
- ✅ Port binding and network access
- ✅ Settings file integration

### Usage:
```bash
# Test web service
python3 test_web_service.py

# Stop web service after testing
python3 test_web_service.py stop

# Test direct Flask mode (development)
python3 test_web_service.py direct
```

### Key Features:
- **Multiple modes** - Service mode vs direct Flask
- **HTTP testing** - Validates web interface responses
- **API validation** - Tests settings endpoints
- **Port checking** - Ensures proper network binding
- **Development mode** - Direct Flask testing for debugging

### Expected Output:
```
[WEB-TEST] === Web Service Test ===
[WEB-TEST] Testing web service on port 8080...
[WEB-TEST] ✓ Web service is running on port 8080
[WEB-TEST] ✓ Settings page is accessible
[WEB-TEST] ✓ API endpoint is working
[WEB-TEST] Web service test PASSED
```

---

## 📁 `test_smb_service.py`

**Purpose**: Tests SMB file sharing functionality with guest access

### What it tests:
- ✅ Samba installation and configuration
- ✅ Guest access setup with `nobody` account
- ✅ Directory permissions for file deletion
- ✅ Network share accessibility
- ✅ File operations (create, read, delete)
- ✅ NetBIOS name resolution
- ✅ Cross-platform access paths

### Usage:
```bash
# Test SMB service
python3 test_smb_service.py

# Stop SMB services after testing
python3 test_smb_service.py stop
```

### Key Features:
- **Guest access** - No passwords required
- **Full permissions** - Create, modify, delete files
- **Network testing** - Local and remote accessibility
- **Permission setup** - Automatic directory configuration
- **Cross-platform** - Windows, macOS, Linux compatibility
- **Hostname integration** - Uses Pi serial for unique identification

### Expected Output:
```
[SMB-TEST] === SMB (Samba) Service Test ===
[SMB-TEST] ✓ Samba is already installed
[SMB-TEST] ✓ Shared directory created and configured
[SMB-TEST] ✓ SMB configuration installed
[SMB-TEST] ✓ SMB services started
[SMB-TEST] ✓ FileShare is accessible
[SMB-TEST] Access from Windows: \\41c4d5f3\FileShare
[SMB-TEST] Access from Linux: smb://41c4d5f3.local/FileShare
```

---

## 🔧 Usage Patterns

### Development Workflow:
```bash
# Test individual components during development
python3 test_camera_service.py    # Test camera changes
python3 test_web_service.py       # Test web interface changes  
python3 test_smb_service.py       # Test file sharing changes
```

### Deployment Validation:
```bash
# After installation, validate all services
python3 test_camera_service.py && \
python3 test_web_service.py && \
python3 test_smb_service.py
```

### Debugging Specific Issues:
```bash
# Camera problems
python3 test_camera_service.py

# Web interface not loading
python3 test_web_service.py direct

# File sharing not working
python3 test_smb_service.py
```

---

## 🛠️ Common Troubleshooting

### Permission Issues:
```bash
# Fix common permission problems
sudo chmod 755 /home/pi
sudo chmod 777 /home/pi/shared
sudo chown -R pi:pi /home/pi/shared
```

### Service Conflicts:
```bash
# Stop all services before testing
sudo systemctl stop camcontroller.service
sudo systemctl stop camcontroller-web.service  
sudo systemctl stop smbd nmbd
```

### Network Issues:
```bash
# Check port availability
sudo netstat -tlnp | grep -E ':(8080|8081|139|445)'

# Test connectivity
ping $(hostname).local
```

---

## 📊 Integration with Install Scripts

These test scripts are designed to work with the optimized installation system:

1. **During installation** - Validate each service as it's configured
2. **After installation** - Comprehensive system testing
3. **Development** - Individual component testing
4. **Maintenance** - Service health checking

### Integration Example:
```python
# In install script
setup_camera_service()
if test_camera_service():
    log("✓ Camera service validated")
else:
    log("✗ Camera service failed validation")
```

---

## 🎯 Benefits

- **Isolated testing** - Test one component without affecting others
- **Clear feedback** - Immediate success/failure indication  
- **Debugging aid** - Pinpoint specific service issues
- **Development speed** - Quick validation during changes
- **Production ready** - Validate deployments before use
- **Cross-platform** - Works on all Pi models and OS versions

These test scripts make PyRpiCamController development and deployment much more reliable and efficient! 🚀