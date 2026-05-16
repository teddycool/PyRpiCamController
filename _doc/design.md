# Design Choices and Rules

## Key Principles

- SD image for complete system and base configuration
- Settings managed from server
- Configuration handled by settings from server or via SSH
- No writing to SD card
- SSH enabled with documented account access

## Basics

### Architecture Overview

The PyRpiCamController follows a modular, event-driven architecture:

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Settings API   │    │   Main Loop     │
│   (Flask)       │◄──►│  (JSON Schema)  │◄──►│   (Game Loop)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────────────────────┼─────────────────┐
                       │                                 │                 │
            ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
            │  Camera States  │    │  IO Controllers │    │  Publishers     │
            │  (Cam/Stream)   │    │  (Light/LED)    │    │  (File/HTTP)    │
            └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### State Management

- **Cam State**: Captures images at configured intervals
- **Stream State**: Provides real-time video streaming
- **Post State**: Handles image processing and publishing

### Configuration Philosophy

- **Single Source of Truth**: JSON schema defines all settings
- **Multi-Interface Access**: Web GUI, API, and file-based configuration
- **Apply Workflow**: Settings changes are persisted and applied through service restart

### Hardware Abstraction

- **Camera Interface**: Pluggable camera modules (PiCam3, PiCamHQ)
- **IO Control**: PWM lighting and RGB status indicators
- **Connectivity**: WiFi management with fallback access point

