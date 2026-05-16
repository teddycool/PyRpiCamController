# PyRpiCamController

A modern Python camera control system for Raspberry Pi with a web interface, designed for research, time-lapse photography, and automated image collection.

**First Release**: This release provides a stable baseline for Raspberry Pi camera deployments, including capture, streaming, web-based configuration, and network file sharing.

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)
[![Raspberry Pi](https://img.shields.io/badge/platform-raspberry%20pi-red.svg)](https://raspberrypi.org)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)

## What Is PyRpiCamController?

PyRpiCamController was originally developed for bee research and machine-learning data collection.

- Automated photography with configurable intervals
- Live streaming with web viewer
- Browser-based configuration and control
- Motion-aware vision pipeline support
- Hardware integration for light and status indicators
- Metadata collection and backend posting support

Use cases include wildlife monitoring, time-lapse projects, security applications, and other automated photography setups.

If you want to support the project, consider donating via [PayPal](https://www.paypal.com/donate/?business=6X9PRDMLYC4NN&no_recurring=1&currency_code=SEK).

## Table of Contents

- [Features](#features)
- [Setup and Operation Flow](#setup-and-operation-flow)
- [Quick Start](#quick-start)
- [Release Readiness Checklist](#release-readiness-checklist)
- [Release Notes](#release-notes)
- [Documentation](#documentation)
- [API](#api)
- [Hardware Support](#hardware-support)
- [Contributing](#contributing)
- [Examples](#examples)
- [Hardware Gallery](#hardware-gallery)
- [License](#license)
- [Support](#support)

## Setup and Operation Flow

[![PyRpiCamController setup and operation flow](_doc/Setup-and-operation-flow.png)](_doc/Setup-and-operation-flow.png)

## Features

### Core Functionality

- Multi-camera support (PiCam2, PiCam3, PiCamHQ, USB webcam fallback)
- Unified settings system with schema-backed validation
- Real-time streaming with configurable resolution and framerate
- Time-based capture scheduling
- Pluggable vision pipeline
- CPU and environmental temperature monitoring
- Built-in network file sharing for images/logs

### Advanced Features

- Web configuration with auto-save and apply/restart workflow
- Internal REST API for UI integration
- Multi-destination logging (console/file/HTTP)
- Hardware control for light and status LEDs
- WiFi onboarding via captive portal flow
- Systemd service integration for production operation

### Default Settings in This Release

Defaults are defined in `Settings/settings_schema.json`.

- File publishing enabled (`Cam.publishers.file.publish = true`)
- Disk space management enabled (`storage_management.enabled = true`)
- File logging enabled (`LogToFile = true`)
- Vision framework enabled (`Vision.enabled = true`)

### Technical Highlights

- Modular architecture for cameras, publishers, and processors
- Concurrent streaming and service-based deployment
- Restart-safe settings persistence
- All-Python implementation with clear structure

## Quick Start

**Prerequisites**: Raspberry Pi 3B+, 4B, or 5 with camera module, WiFi, and USB boot capability.

1. **Get the code**

   ```bash
   git clone https://github.com/teddycool/PyRpiCamController.git
   cd PyRpiCamController
   ```

2. **Install on the Pi**

   ```bash
   scp -r PyRpiCamController pi@your-pi-ip:~/
   ssh pi@your-pi-ip
   cd PyRpiCamController
   python3 tools/install-all-optimized.py
   ```

3. **Configure**

   Open `http://your-pi-ip`.

4. **Monitor service status**

   ```bash
   sudo systemctl status camcontroller.service
   ```

Need full setup details? See [INSTALLATION.md](INSTALLATION.md).

## Release Readiness Checklist

- Validate installer on Raspberry Pi 3B+, 4B, and 5
- Verify first-boot WiFi onboarding via Comitup
- Verify Web UI settings workflow and apply/restart behavior
- Verify camera mode and stream mode behavior
- Verify SMB access for images and logs
- Verify required services are active
- Verify startup self-heal behavior after unclean shutdown

Recommended smoke tests:

```bash
sudo systemctl status camcontroller.service camcontroller-web.service
hostname -I
ls -lah /home/pi/shared/
journalctl -u camcontroller.service -n 100 --no-pager
```

## Release Notes

- Draft release notes: [RELEASE_NOTES.md](RELEASE_NOTES.md)

## Documentation

- [INSTALLATION.md](INSTALLATION.md) — Installation and setup
- [USER_GUIDE.md](USER_GUIDE.md) — End-user guide (English)
- [USER_GUIDE_SWE.md](USER_GUIDE_SWE.md) — End-user guide (Swedish)
- [ARCHITECTURE.md](ARCHITECTURE.md) — Technical architecture
- [Settings/UNIFIED_SETTINGS_GUIDE.md](Settings/UNIFIED_SETTINGS_GUIDE.md) — Settings system
- [SMB_FILE_SHARING.md](SMB_FILE_SHARING.md) — SMB setup and troubleshooting

## API

Main backend endpoints used by the bundled Web UI:

- `GET /api/stream/status`
- `POST /api/settings`
- `POST /api/settings/update`
- `GET /api/settings/pending`
- `POST /api/service/apply-and-restart`
- `GET /api/updates/status`
- `POST /api/updates/check`
- `POST /api/updates/apply`
- `GET /api/updates/changelog`
- `POST /api/updates/backup`

## Hardware Support

### Cameras

- Raspberry Pi Camera Module 2
- Raspberry Pi Camera Module 3
- Raspberry Pi High Quality Camera
- USB webcam (fallback)

### Boards

- Raspberry Pi 3B+
- Raspberry Pi 4B
- Raspberry Pi 5

## Contributing

Contributions are welcome.

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before starting
- Follow patterns in [.dev-guidelines](.dev-guidelines)
- Keep docs and installer updates in sync with code changes

## Examples

- Beehive monitoring
- Flower visitor documentation
- Wildlife and laboratory monitoring
- Time-lapse studies

## Hardware Gallery

![Rpi3 with PiCam3](_doc/rpi3_picam3.jpg)
![Rpi3 with HQ camera](_doc/rpi3-hq-cam.jpg)
![Beehive cam](_doc/bikupekamera_ln.png)
![Beehive camera systems](_doc/bee-hive-cams.jpg)

## License

Licensed under GNU GPLv3. See [LICENSE](LICENSE).

## Support

- Issues: [GitHub Issues](https://github.com/teddycool/PyRpiCamController/issues)
- Discussions: [GitHub Discussions](https://github.com/teddycool/PyRpiCamController/discussions)
- Installation help: [INSTALLATION.md](INSTALLATION.md)
- Architecture details: [ARCHITECTURE.md](ARCHITECTURE.md)
