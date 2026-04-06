# Software Architecture

Technical documentation for PyRpiCamController architecture, design patterns, and implementation details.

## Overview

The PyRpiCamController is designed as a robust, modular camera control system for Raspberry Pi. The basic function is to take pictures at configurable intervals and send those to a backend, with additional features for video streaming, motion detection, and hardware control.

## Core Architecture Patterns

### Game Loop Pattern

The software architecture follows a 'game-loop' pattern with a main loop that orchestrates all camera operations:

```
┌─────────────────┐
│   Main Loop     │
│   (Continuous)  │
└─────┬───────────┘
      │
      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Init State    │───▶│   Cam State     │───▶│   Post State    │
│   (Startup)     │    │   (Capture)     │    │   (Process)     │
└─────────────────┘    └─────────────┬───┘    └─────────────────┘
                                     │
                                     ▼
                       ┌─────────────────┐
                       │  Stream State   │
                       │  (Live Video)   │
                       └─────────────────┘
```

The mainloop is a while-loop that runs until the program is stopped or killed. Different behaviors are implemented as different cam-states, and the mainloop updates the state that is currently active.

### State Machine Implementation

Each state encapsulates specific camera behavior:

- **Init State**: System initialization, hardware setup, settings validation
- **Cam State**: Image capture at configured intervals, motion detection
- **Stream State**: Real-time video streaming to web interface
- **Post State**: Image processing, file saving, backend posting

State transitions are controlled by:
- User configuration (Mode setting: "Cam" or "Stream")
- System conditions (temperature monitoring, connectivity)
- Time-based scheduling

## System Components

### 1. Settings Management System

The software uses a **modern unified settings system** based on JSON schema with comprehensive validation:

```
Settings Architecture:
├── settings_schema.json     # Single source of truth - all defaults and validation
├── settings_manager.py      # Python API for code access  
├── user_settings.json       # User overrides (runtime configurable)
└── hwconfig.py             # Hardware configuration (restart required)
```

**Configuration Methods:**
* **Web Interface**: User-friendly web GUI at `http://your-pi-ip` with auto-save functionality
* **Direct API**: RESTful API for programmatic configuration
* **Settings Files**: Direct JSON configuration for advanced users

**Settings Categories:**
- **Dynamic Settings**: Runtime configurable via web interface (resolution, intervals, logging)
- **Hardware Settings**: Require restart (camera type, GPIO pins, board configuration)

### 2. Camera Abstraction Layer

Pluggable camera interface supporting multiple hardware types:

```python
# CamController/Cam/CamBase.py
def getCam(camtype):
    if (camtype == "PiCam3"):
        return PiCam3.PiCam3()
    if (camtype == "PiCamHQ"):
        return PiCamHQ.PiCamHQ()
```

**Supported Cameras:**
- **PiCam3**: Raspberry Pi Camera Module 3 with autofocus
- **PiCamHQ**: High Quality Camera with interchangeable lenses

**Camera Features:**
- Configurable resolution (up to 4608x2592 for PiCam3)
- Brightness control (-1 to 1 range)
- Auto-focus support

### 3. Streaming Server Architecture

Real-time video streaming with automatic camera detection:

```python
# ModernStreamingServer architecture
class CameraStreamer:
    def detect_camera_system():
        # Try Picamera2 first (preferred)
        # Fallback to OpenCV if needed
        
    def start_streaming():
        # Configure camera based on settings
        # Start HTTP server for video stream
        # Handle concurrent connections
```

**Streaming Features:**
- Automatic camera system detection (Picamera2 → OpenCV fallback)
- Configurable resolution and framerate
- Concurrent client support
- Web-based viewing interface

### 4. Hardware Control System

GPIO-based control for additional hardware:

```python
hwconfig = {
    "CamChip": "PiCam3",           # Camera module type
    "RpiBoard": "Rpi3B+",          # Board identification  
    "LightBox": True,              # Enable light control
    "Io": {
        "lightcontrolgpio": 12,     # PWM light control (GPIO 12)
        "displaycontrolgpio": 18,   # Status LED control (GPIO 18)
        "displaysize": 1,           # Number of LEDs
    },
}
```

**Hardware Capabilities:**
- **Light Control**: PWM-based lighting with 2500Hz frequency (flicker-free)
- **Status Indicators**: Addressable RGB LEDs for system status
- **Temperature Monitoring**: CPU temperature with automated cooling actions

### 5. Network File Server (SMB/CIFS)

Integrated Samba server providing network access to captured images and system logs:

```
SMB Share Structure:
┌─────────────────────────────────────────┐
│ Network Share: \\pi-hostname\shared      │
├─────────────────────────────────────────┤
│ /home/pi/shared/                        │
│ ├── images/                             │
│ │   ├── YYYY-MM-DD/                     │
│ │   │   └── HHMMSS_metadata.jpg        │
│ │   └── thumbnails/ (future)            │
│ └── logs/                               │
│     ├── cam.log (rotating)              │
│     ├── cam.log.1                       │
│     └── system.log                      │
└─────────────────────────────────────────┘
```

**SMB Configuration:**
- **Authentication**: Guest access enabled (no username/password required)
- **Permissions**: Full read/write access for all network users
- **Protocol**: SMB/CIFS compatible with Windows, Mac, Linux, mobile devices
- **Auto-Discovery**: Visible in network neighborhood/network browser
- **Security**: Local network access only (not exposed to internet)

**File Organization:**
```
Image Naming Convention:
├── 20240323/                    # Date-based folders
│   ├── 143022_cam_001.jpg      # HHMMSS_source_sequence.jpg
│   └── 143055_motion_002.jpg   # Motion-triggered capture
```

**Access Control:**
- **Network Isolation**: SMB server binds only to local network interfaces
- **No External Access**: Firewall rules prevent internet access to SMB ports  
- **Guest Mode**: Simplified access without user management complexity
- **Write Protection**: Optional read-only mode via configuration

**Performance Optimization:**
- **USB Storage**: High-speed writes to USB drive (3-5x faster than SD)
- **Async I/O**: Non-blocking image saves during capture
- **Log Rotation**: Automatic cleanup of old log files
- **Bandwidth Management**: SMB access doesn't interfere with camera operations

## Data Flow Architecture

### Image Capture Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Camera    │───▶│   Capture   │───▶│   Process   │───▶│   Publish   │
│   Hardware  │    │   (Memory)  │    │  (Vision)   │    │  (Processed) │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                  │
                                               ┌──────────────────┼──────────────────┐
                                               │                  ▼                  │
                                               │       ┌─────────────┐               │
                                               │       │ Processing  │               │
                                               │       │  Complete   │               │
                                               │       └──────┬──────┘               │
                                               │              │                      │
                                     ┌─────────┼──────────────┼──────────────┼───────┤
                                     │         ▼              ▼              ▼       │
                                     │ ┌─────────────┐ ┌─────────────┐              │
                                     │ │Local Storage│ │   Remote    │              │
                                     │ │(USB Drive)  │ │HTTP Backend │              │
                                     │ │             │ │(NAS/Server) │              │
                                     │ │file.publish │ │  (posturl)  │              │
                                     │ │   = true    │ │             │              │
                                     │ └─────┬───────┘ └─────────────┘              │
                                     │       │                                      │
                                     │       ▼                                      │
                                     │ ┌─────────────┐                              │
                                     │ │SMB Network  │                              │
                                     │ │Access to    │                              │
                                     │ │Local Files  │                              │
                                     │ └─────────────┘                              │
                                     │                                              │
                                     │  Same processed image → multiple destinations │
                                     └──────────────────────────────────────────────┘
```

**Key Principles:**
**Key Features:**
- **Unified Processing**: All images processed once through the same pipeline
- **Dual Publishing Options**: Same processed image can be published to both destinations:
  - **Local Storage**: High-speed USB drive with SMB network access (`file.publish = true`)
  - **Remote Backend**: HTTP posting to external server/NAS (`posturl` configuration)
- **Independent Configuration**: Enable/disable local and remote publishing separately
- **High-Speed USB Storage**: 3-5x faster writes compared to SD cards for improved performance
- **Network Accessibility**: SMB file sharing provides network access to locally stored images
- **Remote Integration**: HTTP posting to any network-accessible backend
- **Performance Optimized**: Single processing pipeline feeds multiple output channels

### Motion Detection Pipeline

Integrated motion detection with configurable sensitivity:

```python
MotionDetector: {
    "active": True,        # Enable/disable detection
    "motioncount": 200,    # Sensitivity threshold
    "history": 50          # Background model frames
}
```

## Logging Architecture

Multi-destination logging with structured output:

```python
Logging Destinations:
├── Console Output      # Always enabled for debugging
├── File Logging       # Rotating logs with size limits  
└── HTTP Logging       # Backend server posting (optional)
```

**Log Configuration:**
- **Levels**: Debug, Info, Warning, Error
- **Formats**: Human-readable (console), JSON (file/HTTP)
- **Rotation**: Configurable file size and backup count
- **Metadata**: CPU ID, timestamp, log level, component name

**HTTP Logging:**
Structured JSON posting to configurable backend URL. Example backend receiver provided in `backend/` directory.

## Service Architecture

Systemd service integration for production deployment:

```bash
# Main camera controller service
sudo systemctl status camcontroller.service

# Web interface service  
sudo systemctl status camcontroller-web.service
```

**Service Features:**
- Automatic startup on boot
- Process monitoring and restart
- Centralized logging via journalctl
- Resource management and limits

## Network Architecture

### WiFi Management

Integrated with Comitup for zero-touch network configuration:

```
Boot Sequence:
├── Try Known Networks
├── Scan for Configured SSIDs  
├── Fallback to Access Point Mode
└── Captive Portal for Configuration
```

**Network Features:**
- Headless WiFi setup via captive portal
- Automatic fallback to access point mode
- No keyboard/monitor required for configuration
- Persistent network configuration

### Web Interface

Flask-based web application for configuration:

```
Web Interface Architecture:
├── Auto-generated Forms    # From settings schema
├── RESTful API            # Programmatic access
├── Real-time Validation   # Client-side feedback
└── Auto-save             # Persistent settings
```

## Performance Characteristics

### Resource Usage

- **Storage**: High-speed USB drives provide 3-5x faster I/O compared to SD cards
- **Memory**: Efficient in-memory image processing with USB buffering
- **CPU**: Reduced load due to faster storage I/O operations
- **Network**: Efficient streaming with SMB file sharing and configurable quality
- **Disk Management**: Rotating logs with automatic cleanup and size limits

### USB Storage Benefits

- **Write Performance**: 15-50 MB/s typical (vs 3-10 MB/s for SD cards)
- **Random I/O**: Significantly faster for log file operations
- **Reliability**: Better wear leveling and error handling than SD cards
- **Longevity**: Designed for continuous operation in computing environments

### Scalability Features

- **Concurrent Access**: SMB file sharing doesn't interfere with camera operations
- **Multiple Clients**: Simultaneous streaming and file access
- **Background Processing**: Non-blocking image capture with fast storage writes
- **Configurable Intervals**: Balance between data collection and system load
- **Temperature Monitoring**: Automatic throttling on overheating

## Extension Points

The architecture supports easy extension:

### Adding New Camera Types

1. Implement `CamBase` interface in new module
2. Add camera type to `getCam()` function
3. Update hardware configuration options

### Custom Processing Pipelines

1. Extend state machine with new states
2. Implement processing logic in state handlers
3. Configure via settings schema

### Backend Integrations

1. Implement HTTP posting protocols
2. Add authentication methods
3. Configure via settings system

For more details, see the Settings/ directory documentation and individual module documentation within the codebase.