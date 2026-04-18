# Comitup Troubleshooting Guide

## Problem Description
Comitup service failing with NetworkManager error:
```
dbus.exceptions.DBusException: org.freedesktop.NetworkManager.UnknownConnection: 
Connection 'AP-cd325f0f-0000' is not available on device wlan0 because device is not available
```

## Root Cause Analysis
This error typically occurs when:

1. **WiFi Hardware Detection Issue**: wlan0 interface not detected by NetworkManager
2. **Service Timing Conflict**: comitup starts before WiFi hardware is ready  
3. **USB Boot Hardware Delay**: USB boot systems may have delayed hardware enumeration
4. **Driver/Masking Issues**: Conflicting network service configurations

## Diagnostic Steps

### 1. First, Run Diagnostics
```bash
# Copy to Pi and run:
sudo ./tools/diagnose_comitup.sh
```

This will show:
- WiFi hardware status
- NetworkManager device list
- Service status and logs
- Configuration files

### 2. Apply Main Fix
```bash
# Run on Pi as root:
sudo ./tools/fix_comitup.sh
```

This script:
- Reloads WiFi drivers
- Configures NetworkManager properly
- Ensures correct service order
- Re-masks conflicting services
- Validates functionality

### 3. USB Boot Specific Fix (if needed)
```bash
# If still failing on USB boot system:
sudo ./tools/fix_usb_boot_wifi.sh
sudo reboot
```

This adds:
- Hardware detection delays
- systemd service dependencies  
- udev rules for WiFi enumeration

## Manual Verification

After running fixes, verify:

```bash
# Check WiFi device
nmcli device status | grep wifi

# Check services
sudo systemctl status NetworkManager
sudo systemctl status comitup

# Monitor logs
sudo journalctl -u comitup.service -f
```

## Expected Behavior

When working correctly:
- WiFi device shows as "wifi" in `nmcli device status`
- comitup creates AP named `AP-<hostname>` (e.g., `AP-cd325f0f`)
- No DBusException errors in logs
- Can connect to AP for WiFi configuration

## Fallback Options

If all fixes fail:

1. **Manual WiFi Configuration**:
   ```bash
   sudo nmcli device wifi connect "YourWiFi" password "YourPassword"
   ```

2. **Disable comitup temporarily**:
   ```bash
   sudo systemctl disable comitup
   sudo systemctl stop comitup
   ```

3. **Use ethernet connection** for initial setup

## Files Created/Modified

- `/etc/NetworkManager/NetworkManager.conf` - Ensures WiFi management
- `/etc/systemd/system/comitup.service.d/override.conf` - Hardware detection delay
- `/etc/udev/rules.d/99-wifi-usb-boot.rules` - WiFi hardware detection rule

## Support

If issues persist, collect logs:
```bash
sudo journalctl -u comitup.service --no-pager > comitup.log
sudo journalctl -u NetworkManager.service --no-pager > nm.log
nmcli device status > device_status.txt
```