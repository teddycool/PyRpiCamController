# Installation Guide

This guide installs PyRpiCamController on Raspberry Pi and verifies core services.

## Requirements

- Raspberry Pi 3B+, 4B, or 5
- Raspberry Pi OS (64-bit recommended)
- Camera module supported by the project
- Network access for package installation

## 1) Deploy Project Files

Copy project files to the target Pi (default install path is `/home/pi/PyRpiCamController`).

```bash
scp -r PyRpiCamController pi@your-pi-ip:~/
ssh pi@your-pi-ip
cd ~/PyRpiCamController
```

## 2) Run Installer

```bash
python3 tools/install-all-optimized.py
```

Installer responsibilities include:

- OS/package dependencies
- Service files and enablement
- Shared directories and permissions
- SMB-related setup (if enabled)
- Pigpio daemon setup for hardware PWM path

## 3) Verify Services

```bash
sudo systemctl status camcontroller.service --no-pager
sudo systemctl status camcontroller-web.service --no-pager
sudo systemctl status pigpiod --no-pager
```

Expected:

- `camcontroller.service`: active
- `camcontroller-web.service`: active
- `pigpiod.service`: active

## 4) Open Web UI

Open in browser:

- `http://your-pi-ip`

Apply setting changes using **Apply Changes & Restart Service**.

## 5) Hardware Configuration

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

## 6) PWM Notes (Important)

- Light PWM does **not** use `RPi.GPIO` software fallback.
- Light backend order: `pigpio` preferred, `lgpio` fallback.
- If Light and Display pins conflict on PWM resources (for example GPIO12 + GPIO18), Light is prioritized and Display output may be disabled.

Backend check:

```bash
UNIT='camcontroller.service'
journalctl -u "$UNIT" -n 120 --no-pager | grep 'cam.light'
```

## 7) Smoke Test Commands

```bash
sudo systemctl status camcontroller.service camcontroller-web.service --no-pager
hostname -I
ls -lah /home/pi/shared/
journalctl -u camcontroller.service -n 120 --no-pager
```

## 8) Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for startup, settings, PWM backend, and stream diagnostics.
