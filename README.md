# PyRpiCamController

A modern Python camera control system for Raspberry Pi with a web interface, designed for research, time-lapse photography, and automated image collection.

**First Release**: This release delivers a stable and practical baseline for Raspberry Pi camera deployments, including capture, streaming, web-based configuration, and network file sharing. It is intended for real-world use while selected advanced vision features continue to mature.

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)
[![Raspberry Pi](https://img.shields.io/badge/platform-raspberry%20pi-red.svg)](https://raspberrypi.org)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)

## 🎯 What is PyRpiCamController?

A comprehensive camera control system originally developed for bee research and machine-learning data collection. The system provides:

- **Automated Photography**: Configurable time-lapse
- **Live Streaming**: Real-time video streaming with web viewer
- **Web Interface**: Modern browser-based configuration and control
- **Motion-Aware Processing**: Detect and annotate movement in the vision pipeline
- **Hardware Integration**: LED lighting control and status indicators
- **Research Ready**: Metadata collection and backend data posting

It is well suited for wildlife monitoring, time-lapse projects, security applications, and other automated photography needs.

If you like the project and want to support it, consider donating a small amount via [PayPal](https://www.paypal.com/donate/?business=6X9PRDMLYC4NN&no_recurring=1&currency_code=SEK)

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Hardware Support](#hardware-support)
- [Contributing](#contributing)
- [Examples](#examples)
- [Hardware Gallery](#hardware-gallery)

## ✨ Features

### Core Functionality
* **Multi-Camera Support**: Raspberry Pi Camera Module 2/3 and HQ Camera
* **Unified Settings System**: JSON schema-based configuration with web interface
* **Real-time Streaming**: Live video with configurable resolution and framerate
* **Smart Scheduling**: Time-based capture with customizable intervals
* **Vision Pipeline**: Pluggable image processing pipeline (base pipeline enabled)
* **Temperature Monitoring**: CPU thermal management with automatic cooling
* **Built-in Network Storage**: Automatic file sharing for images and logs

### Advanced Features
* **Web Configuration**: Browser-based settings management with auto-save
* **RESTful API**: Programmatic control and integration
* **Multi-destination Logging**: File, console, and HTTP backend logging
* **Hardware Control**: PWM lighting (2500Hz flicker-free) and RGB status LEDs (needs auxiliary hardware)
* **Network Management**: WiFi setup via captive portal (zero-touch configuration)
* **Service Integration**: Systemd services for production deployment
* **Research Features**: Metadata collection, backend posting, structured logging

### Default-Enabled In This Release
These features are enabled by default in `Settings/settings_schema.json`:

* **File publishing enabled** (`Cam.publishers.file.publish = true`)
* **Disk space management enabled** (`storage_management.enabled = true`)
* **File logging enabled** (`LogToFile = true`)
* **Vision framework enabled** (`Vision.enabled = true`)

OTA update support is not enabled for production use in this release.

### Technical Highlights
* **Modular Architecture**: Easy to add new camera types, publishing targets, and image processing steps  
* **High Performance**: Concurrent streaming with efficient resource usage
* **Production Ready**: Service deployment with monitoring and auto-restart 
* **All Python**: Easy-to-follow, well-documented, open-source code

### Auxiliary control hardware
* PWM-controlled LED lighting (flicker-free 2500Hz)
* Addressable RGB status indicators  
* Temperature sensors for environmental monitoring
* A circuit diagram for optional auxiliary hardware is available here: [Circuit diagram](_doc/extra_hardware.pdf), and [the PCB can be ordered from Aisler](https://aisler.net/p/VECRZXIU)
* Complete KiCAD project available in [this zip file](_doc/RpiConnector_v2.1_kicad_9.0.7.zip).

## 🚀 Quick Start

**Prerequisites**: Raspberry Pi (3B+, 4B, or 5) with camera module, WiFi, and USB boot capability

1. **Get the Code**:
   ```bash
   git clone https://github.com/teddycool/PyRpiCamController.git
   cd PyRpiCamController
   ```

2. **Install**: Copy to your Pi (running from USB drive) and run the installer:
   ```bash
   scp -r PyRpiCamController pi@your-pi-ip:~/
   ssh pi@your-pi-ip
   cd PyRpiCamController && python3 tools/install-all-optimized.py
   ```

3. **Configure**: Access the web interface at `http://your-pi-ip`

4. **Monitor**: Check status with `sudo systemctl status camcontroller.service`

📖 **Need detailed setup instructions?** → [INSTALLATION.md](INSTALLATION.md)

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [INSTALLATION.md](INSTALLATION.md) | Complete installation guide with WiFi setup |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture and design details |
| [UNIFIED_SETTINGS_GUIDE.md](Settings/UNIFIED_SETTINGS_GUIDE.md) | Unified settings system documentation |

## 🔧 Hardware Support

### Currently Supported Cameras
- **Raspberry Pi Camera Module 2**: Supported via Picamera2
- **Raspberry Pi Camera Module 3**: Full resolution (4608x2592), autofocus
- **Raspberry Pi High Quality Camera**: Interchangeable lenses, high sensitivity

### Supported Boards  
- **Raspberry Pi 3B+**: USB boot capable (recommended starting point)
- **Raspberry Pi 4B**: All variants with USB 3.0 boot support
- **Raspberry Pi 5**: Full USB boot support

**Note**: Raspberry Pi Zero models and 3B (non-+) are **not supported** out of the box because they cannot boot directly from USB.

### Storage Requirements
- **High-Performance USB Drive**: SanDisk Ultra Fit 32GB+ or similar is recommended
- **USB 3.0+ Support**: For optimal performance with image processing
- **No SD Card**: System runs entirely from USB for superior performance and reliability

### Built-in Network Storage (SMB)
- **Built-in SMB Server**: Automatic file sharing for images and logs
- **Guest Access**: No authentication required for easy access
- **Cross-Platform**: Access from Windows, Mac or Linux via network share
- **Auto-Configuration**: Setup handled by installation script


## 🤝 Contributing

Contributions are very welcome.

**Ways to contribute:**
- 🐛 **Report Issues**: Bug reports, feature requests, and feedback
- 💡 **Feature Requests**: New camera types, processing features, hardware integrations
- 🔧 **Pull Requests**: Code contributions (one feature per PR for easier review)
- 📚 **Documentation**: Improvements to guides and technical documentation
- 🧪 **Testing**: Hardware compatibility testing across Pi models

**Development Focus Areas:**
- Additional camera support (Arducam, USB cameras)
- Advanced computer vision features (YOLO integration)
- Home Assistant sensor integration
- OTA update system (planned)
- Enhanced vision processing pipeline

## 🌟 Examples

Real-world applications of PyRpiCamController:

### 🐝 Beehive Monitoring

**Inside Hive Camera**: Raspberry Pi 3B+ with PiCam3 wide lens and autofocus. Integrated light box and status LED for low-disturbance monitoring. USB storage for reliable 24/7 operation.
[Buy a pre-built beehive camera](https://www.sensorwebben.se/kamera-bikupa/)

**Entrance Monitoring**: Raspberry Pi 4B with PiCam3 in weatherproof enclosure. Status LED and SMB file sharing for remote access to entrance activity data.



### 🌸 Natural Science Research

**Flower Visitor Documentation**: Raspberry Pi 3B+ with PiCamHQ for high-quality macro photography. Ideal for documenting insect behavior and plant interactions.

### 🔬 General Research Applications

- Wildlife monitoring with motion detection
- Time-lapse plant growth studies  
- Laboratory equipment monitoring
- Security and surveillance

## 📸 Hardware Gallery

### Raspberry Pi 3B+ with Camera Module 3
!["Rpi3 with a cam"](_doc/rpi3_picam3.jpg)


### Raspberry Pi with HQ Camera
!["Rpi3 with a HQ camera"](_doc/rpi3-hq-cam.jpg)

### Inside beehive cam
!["Beehive cam"](_doc/bikupekamera_j.png)

### Deployed Beehive Camera Systems
!["Beehive cams"](_doc/bee-hive-cams.jpg)

---

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions, issues, or contributions:
- 📧 **Issues**: [GitHub Issues](https://github.com/teddycool/PyRpiCamController/issues)
- 🤝 **Discussions**: [GitHub Discussions](https://github.com/teddycool/PyRpiCamController/discussions) 
- 💻 **Technical Details**: See [ARCHITECTURE.md](ARCHITECTURE.md) for implementation details
- 🔧 **Installation Help**: See [INSTALLATION.md](INSTALLATION.md) for step-by-step setup