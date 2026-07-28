# Installation Guide

This guide installs PyRpiCamController on Raspberry Pi and verifies core services.

## Requirements

- Raspberry Pi 3B+, 4B, or 5
- Raspberry Pi OS (64-bit recommended)
- Camera module supported by the project
- Network access for package installation

---

## Recommended: Fresh Pi Provisioning (Release-Based)

For a completely fresh Raspberry Pi, use the **automated provisioning script** from your dev machine. This is the fastest and most reliable method.

**Important:** This is the default production path and it assumes a working OTA backend (including secure enrollment endpoints).

### Prerequisites

- Fresh Pi running Pi OS with SSH enabled
- Pi OS should have a static or known IP address on your network
- Development machine has SSH access to the Pi
- Reachable OTA backend and valid admin enrollment credentials

### Provisioning from Dev Machine

```bash
# Non-interactive (quick, uses defaults for hardware config)
python3 tools/provision_fresh_pi.py <pi_ip> <release_version> "<device_name>" "<location>" --non-interactive

# Example:
python3 tools/provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-Front" "Entryway" --non-interactive
```

**What this does automatically:**

1. Downloads the release tarball from GitHub
2. Extracts everything on the Pi
3. Runs the installer with `--non-interactive` (uses default hardware config)
4. Enrolls the device with the backend and gets an API key
5. Verifies all services are running
6. Returns success/failure summary

**For interactive hardware configuration** (prompts for camera, display, features):

```bash
python3 tools/provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-Front" "Entryway"
```

**For custom backend URL** (non-standard OTA server):

```bash
python3 tools/provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-Front" "Entryway" \
    --backend-url https://myserver.com/ota --non-interactive
```

**To skip enrollment** (manual enrollment later):

```bash
python3 tools/provision_fresh_pi.py 192.168.1.50 1.0.0 "Camera-Front" "Entryway" \
    --skip-enrollment --non-interactive
```

See `python3 tools/provision_fresh_pi.py --help` for all options.

If your backend is unavailable or you are testing without backend integration, use the **Alternative: Manual Installation (Advanced)** path below.

### What Gets Provisioned

- PyRpiCamController source code in `~/PyRpiCamController`
- `hwconfig.py` auto-generated with platform detection
- All systemd services (camera controller, web UI, OTA daemon)
- Device enrolled with backend server (API key stored locally)
- OTA daemon configured and running

### After Provisioning

The Pi is ready for production:

```bash
# View camera logs
ssh pi@<pi_ip> "sudo journalctl -u camcontroller -f"

# Check OTA daemon status
ssh pi@<pi_ip> "sudo journalctl -u camcontroller-update -n 50"

# SSH into Pi
ssh pi@<pi_ip>
```

---

## Alternative: Manual Installation (Advanced)

If you prefer to install manually or need to debug, use this method.

This is also the recommended path for local/testing use without a backend.

### 1) Deploy Project Files

Copy project files to the target Pi (default install path is `/home/pi/PyRpiCamController`).

```bash
scp -r PyRpiCamController pi@your-pi-ip:~/
ssh pi@your-pi-ip
cd ~/PyRpiCamController
```

### 2) Run Installer

```bash
python3 tools/install-all-optimized.py
```

Installer responsibilities include:

- OS/package dependencies
- Service files and enablement
- Shared directories and permissions
- SMB-related setup (if enabled)
- Pigpio daemon setup for hardware PWM path

### 3) Verify Services

```bash
sudo systemctl status camcontroller.service --no-pager
sudo systemctl status camcontroller-web.service --no-pager
sudo systemctl status camcontroller-update.service --no-pager
sudo systemctl status pigpiod --no-pager
```

Expected:

- `camcontroller.service`: active
- `camcontroller-web.service`: active
- `camcontroller-update.service`: active
- `pigpiod.service`: active

After first install or service updates, reload units once:

```bash
sudo systemctl daemon-reload
sudo systemctl restart camcontroller.service camcontroller-web.service camcontroller-update.service
```

### 4) Open Web UI

Open in browser:

- `http://your-pi-ip`

Apply setting changes using **Apply Changes & Restart Service**.

### 5) Hardware Configuration

Hardware-specific values live in `CamController/hwconfig.py`.

Example:

```python
hwconfig1 = {
    "CamChip": "PiCam3",
    "RpiBoard": "Rpi4",
    "LightBox": True,
    "Io": {
        "lightcontrolgpio": 12,
        "displaycontrolgpio": 18,
        "displaysize": 1,
        "ds18b20pin": 22,
    },
}
```

After hardware config changes:

```bash
sudo systemctl restart camcontroller.service
```

### 6) PWM Notes (Important)

- Light PWM does **not** use `RPi.GPIO` software fallback.
- Light backend order: `pigpio` preferred, `lgpio` fallback.
- If Light and Display pins conflict on PWM resources (for example GPIO12 + GPIO18), Light is prioritized and Display output may be disabled.

Backend check:

```bash
UNIT='camcontroller.service'
journalctl -u "$UNIT" -n 120 --no-pager | grep 'cam.light'
```

### 7) Smoke Test Commands

```bash
sudo systemctl status camcontroller.service camcontroller-web.service camcontroller-update.service --no-pager
hostname -I
ls -lah /home/pi/shared/
journalctl -u camcontroller.service -n 120 --no-pager
journalctl -u camcontroller-update.service -n 120 --no-pager
```

### 8) OTA Setup Verification

Verify OTA settings and one manual check path:

```bash
python3 -c "from Settings.settings_manager import settings_manager; print('OtaEnable=', settings_manager.get('OtaEnable')); print('server=', settings_manager.get('OTA.server_url')); print('interval=', settings_manager.get('OTA.check_interval'))"

echo "manual check" | sudo tee /tmp/ota_check_trigger
sudo journalctl -u camcontroller-update.service -n 100 --no-pager
```

If OTA backend is production, confirm responses come from `https://www.sensorwebben.se/pycamota`.

### 9) Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for startup, settings, PWM backend, and stream diagnostics.
