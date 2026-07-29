# Installation Guide

This guide covers the release-based production install first, then the manual path for development and debugging.

## Which Installation Path Should I Use?

| Scenario | Recommended Path |
|----------|-----------------|
| Production deployment, backend available | ✅ **[Fresh Pi Provisioning](#recommended-fresh-pi-provisioning-release-based)** (default) |
| Local testing / development / no backend | ✅ **[Manual Installation](#alternative-manual-installation-advanced)** |
| Backend temporarily unavailable | ✅ **[Manual Installation](#alternative-manual-installation-advanced)** |
| Exploring the software for the first time | ✅ **[Manual Installation](#alternative-manual-installation-advanced)** |
| Re-enrolling an existing device | ✅ Fresh Pi Provisioning with `--skip-hwconfig` |
| Batch rollout of new cameras | ✅ **[Fresh Pi Provisioning](#recommended-fresh-pi-provisioning-release-based)** |
| Contributing / editing source on Pi | ✅ **[Manual Installation](#alternative-manual-installation-advanced)** |

---

## Requirements

- Raspberry Pi 3B+, 4B, or 5
- Raspberry Pi OS (64-bit recommended)
- Camera module supported by the project
- Network access for package installation
- `ffmpeg` for YouTube Live publishing (installed automatically by `tools/install-all-optimized.py` and the release package flow)

---

## Recommended: Fresh Pi Provisioning (Release-Based)

For a completely fresh Raspberry Pi, use the **automated provisioning script** from your dev machine. This is the default and most reliable production method.

**Important:** This is the default production path and it assumes a working OTA backend (including secure enrollment endpoints).

### Prerequisites

- Fresh Pi running Pi OS with SSH enabled
- Pi OS with a static or known IP address on your network
- Development machine with SSH access to the Pi
- Reachable OTA backend and valid admin enrollment credentials

### Provisioning from Dev Machine

```bash
# Non-interactive (quick, uses defaults for hardware config)
python3 tools/provision_fresh_pi.py <pi_ip> <release_version> "<device_name>" "<location>" --non-interactive

# Example:
python3 tools/provision_fresh_pi.py 192.168.1.50 1.1.2 "Camera-Front" "Entryway" --non-interactive

# Production-hardened example (install key + disable password SSH)
python3 tools/provision_fresh_pi.py 192.168.1.50 1.1.2 "Camera-Front" "Entryway" \
    --non-interactive --ssh-pubkey ~/.ssh/id_ed25519.pub --ssh-posture key-only
```

**What this does automatically:**

1. Downloads the release tarball from GitHub
2. Extracts everything on the Pi
3. Runs the installer with `--non-interactive` (uses default hardware config)
4. Enrolls the device with the backend and gets an API key
5. Verifies all services are running
6. Optionally hardens SSH posture (`--ssh-posture key-only|disable`)
7. Returns success/failure summary

**For interactive hardware configuration** (prompts for camera, display, features):

```bash
python3 tools/provision_fresh_pi.py 192.168.1.50 1.1.2 "Camera-Front" "Entryway"
```

**For custom backend URL** (non-standard OTA server):

```bash
python3 tools/provision_fresh_pi.py 192.168.1.50 1.1.2 "Camera-Front" "Entryway" \
    --backend-url https://myserver.com/ota --non-interactive
```

**To skip enrollment** (manual enrollment later):

```bash
python3 tools/provision_fresh_pi.py 192.168.1.50 1.1.2 "Camera-Front" "Entryway" \
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
- `ffmpeg` installation for YouTube Live streaming

### YouTube Live and Hardware Acceleration Notes

- YouTube Live uses the MJPEG camera stream and re-encodes it with FFmpeg before pushing over RTMPS.
- The current production path uses `libx264` with `ultrafast` for reliability and lower CPU latency on Raspberry Pi.
- Hardware H.264 encoders are not required for normal operation and are not the default path in this release.
- If you tune YouTube Live FPS, keep bitrate and network upload capacity in mind.

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

### YouTube Live Configuration

YouTube Live settings are exposed in the Web GUI under **Kamera → Advanced**.

Available settings:

- `Cam.publishers.youtube.publish` — enable/disable publishing
- `Cam.publishers.youtube.rtmps_url` — YouTube RTMPS ingest URL
- `Cam.publishers.youtube.stream_key` — stream key
- `Cam.publishers.youtube.bitrate` — 1500k / 2500k / 4000k / 6000k
- `Cam.publishers.youtube.fps` — 5 / 10 / 15 / 20

Recommended defaults for Raspberry Pi 3B+:

- bitrate: `1500k`
- FPS: `10`

If the stream falls behind, lower the FPS first, then reduce bitrate if needed.

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
