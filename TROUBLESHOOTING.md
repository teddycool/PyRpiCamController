# Troubleshooting Guide

Common issues and fixes for the current PyRpiCamController implementation.

## Quick Triage

Run these first to get a fast health snapshot:

```bash
cd /home/pi/PyRpiCamController

# Core services
sudo systemctl status camcontroller.service
sudo systemctl status camcontroller-web.service
sudo systemctl status camcontroller-update.service

# Recent logs for all project services
sudo journalctl -u camcontroller.service -u camcontroller-web.service -u camcontroller-update.service --since "30 minutes ago"

# One-shot install validation helper
bash tools/validate_installation.sh
```

## Service Architecture (Current)

The runtime is split into three systemd services:

- `camcontroller.service`: main camera loop (`CamController/Main.py`)
- `camcontroller-web.service`: Flask app served by Gunicorn on port `80`
- `camcontroller-update.service`: OTA daemon (`Updates/camcontroller_update_daemon.py --daemon`)

If one service fails, check its dedicated logs first:

```bash
sudo journalctl -u camcontroller.service -f
sudo journalctl -u camcontroller-web.service -f
sudo journalctl -u camcontroller-update.service -f
```

## Settings Not Applying

### How settings apply now

Settings changed in the web UI are tracked as pending and written to:

- `/tmp/webgui_pending_changes.json`

When you click **Apply Changes & Restart Service** in the UI, the web app:

1. Persists pending settings to `Settings/user_settings.json`
2. Writes `/tmp/cam_reload_settings.txt` with `reload_settings`
3. Lets `camcontroller.service` reload settings in-process

This is a live settings reload path (not a forced full systemd restart).

### If UI changes do not take effect

```bash
# Check pending changes file created by WebGui
sudo cat /tmp/webgui_pending_changes.json

# Check reload trigger file (should be consumed quickly by camcontroller)
ls -l /tmp/cam_reload_settings.txt

# Confirm settings actually persisted
sudo cat /home/pi/PyRpiCamController/Settings/user_settings.json

# Check for reload handling errors
sudo journalctl -u camcontroller.service --since "10 minutes ago" | grep -Ei "reload|settings|mode"
```

If needed, force a full restart:

```bash
sudo systemctl restart camcontroller.service
```

## CamController Service Won't Start

### Primary checks

```bash
sudo systemctl status camcontroller.service
sudo journalctl -u camcontroller.service -n 200 --no-pager
```

### Common root causes

1. Missing camera stack (`picamera2` / `libcamera`) on non-Pi environments

```bash
python3 -c "from picamera2 import Picamera2; print('ok')"
libcamera-hello --list-cameras
```

2. Broken settings JSON or invalid values

```bash
python3 -c "from Settings.settings_manager import settings_manager; print(settings_manager.get('Mode'))"
python3 -c "from Settings.settings_manager import settings_manager; print(settings_manager.get('Cam.resolution'))"
```

3. Hardware config mismatch

```bash
python3 -c "from CamController.hwconfig import hwconfig1; print(hwconfig1['CamChip'])"
```

### Permission issues on settings file

`camcontroller.service` already tries to fix ownership/permissions before startup. If it still fails:

```bash
sudo chown pi:pi /home/pi/PyRpiCamController/Settings/user_settings.json
sudo chmod 664 /home/pi/PyRpiCamController/Settings/user_settings.json
sudo systemctl restart camcontroller.service
```

## Web Interface Issues

### Service fails to start

```bash
sudo systemctl status camcontroller-web.service
sudo journalctl -u camcontroller-web.service -n 200 --no-pager
```

`camcontroller-web.service` uses:

- `ExecStart=/usr/bin/gunicorn -w 2 -b 0.0.0.0:80 web_app:app`
- `AmbientCapabilities=CAP_NET_BIND_SERVICE`
- `CapabilityBoundingSet=CAP_NET_BIND_SERVICE`
- `WorkingDirectory=/home/pi/PyRpiCamController/WebGui`
- `Environment=PYTHONPATH=/home/pi/PyRpiCamController`

If logs show repeated `Can't connect to ('0.0.0.0', 80)`, confirm the capability lines are present in the installed unit and then reload systemd:

```bash
sudo systemctl cat camcontroller-web.service
sudo cp /home/pi/PyRpiCamController/Services/camcontroller-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart camcontroller-web.service
```

If Gunicorn binary is missing:

```bash
which gunicorn
dpkg -l | grep -i gunicorn
```

### Web UI unreachable

```bash
# Check listener on port 80
sudo ss -tulpn | grep :80

# Local health check
curl -sS http://localhost/api/test
```

### Manual foreground run for debugging

```bash
cd /home/pi/PyRpiCamController/WebGui
export PYTHONPATH=/home/pi/PyRpiCamController
python3 web_app.py
```

## OTA Update Issues

### Update checks do not run

```bash
sudo systemctl status camcontroller-update.service
sudo journalctl -u camcontroller-update.service -f
python3 -c "from Settings.settings_manager import settings_manager; print('OtaEnable=', settings_manager.get('OtaEnable')); print('interval=', settings_manager.get('OTA.check_interval'))"
```

### Manual trigger files

The OTA daemon processes these files:

- `/tmp/ota_check_trigger`
- `/tmp/ota_apply_trigger`

Create triggers manually if needed:

```bash
echo "manual check" | sudo tee /tmp/ota_check_trigger
echo "manual apply" | sudo tee /tmp/ota_apply_trigger
sudo journalctl -u camcontroller-update.service -n 100 --no-pager
```

## SMB/Samba File Sharing Issues

### Share names and behavior

Current Samba config exposes:

- `shared` (primary, browseable)
- `FileShare` (legacy alias, not browseable)

Both map to `/home/pi/shared` with guest access.

### Connection refused or timeout

```bash
sudo systemctl status smbd nmbd
sudo systemctl restart smbd nmbd
sudo ss -tulpn | grep -E ':139|:445'
testparm /etc/samba/smb.conf
ls -la /home/pi/shared/
```

### Access examples

- Windows: `\\your-pi-ip\shared`
- macOS: `smb://your-pi-ip/shared`
- Linux file manager: `smb://your-pi-ip/shared`

If hostname resolution fails, use IP address directly.

## WiFi / Comitup Issues

If no known network is available, the device should expose a `comitup-*` access point.

```bash
sudo systemctl status comitup
sudo journalctl -u comitup -f
```

If installed, `comitup-cli` can also be used for diagnostics.

## Camera Detection and Capture Issues

```bash
libcamera-hello --list-cameras
libcamera-still -o /tmp/test.jpg --width 1920 --height 1080
```

Also verify hardware and thermal state:

```bash
vcgencmd get_camera
vcgencmd measure_temp
```

## Logs and Diagnostics

### Most useful logs

```bash
# Main camera runtime
sudo journalctl -u camcontroller.service --since "1 hour ago"

# Web API/runtime
sudo journalctl -u camcontroller-web.service --since "1 hour ago"

# OTA daemon
sudo journalctl -u camcontroller-update.service --since "1 hour ago"

# Optional file log if LogToFile is enabled
tail -n 100 /home/pi/shared/logs/cam.log
```

### System resources

```bash
df -h
free -h
uptime
```

## Reset and Recovery

### Reset runtime settings

```bash
cd /home/pi/PyRpiCamController/Settings
cp -f user_settings.json user_settings.json.backup 2>/dev/null || true
rm -f user_settings.json
sudo systemctl restart camcontroller.service
```

### Reinstall services and dependencies

```bash
cd /home/pi/PyRpiCamController
python3 tools/install-all-optimized.py
sudo systemctl daemon-reload
sudo systemctl restart camcontroller.service camcontroller-web.service camcontroller-update.service
```

## What to Include in a Bug Report

Share these outputs:

1. `sudo systemctl status camcontroller.service camcontroller-web.service camcontroller-update.service`
2. `sudo journalctl -u camcontroller.service -u camcontroller-web.service -u camcontroller-update.service --since "1 hour ago"`
3. `libcamera-hello --list-cameras`
4. `cat /home/pi/PyRpiCamController/VERSION`
5. `python3 -c "from Settings.settings_manager import settings_manager; print(settings_manager.get('Mode'))"`