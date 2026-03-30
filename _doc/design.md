# Design Choices and Rules

## Key Principles

* SD-image for complete system and a base-configuration
* Settings from server
* Everything handled by settings either from server or via SSH
* No writing to SD-card
* SSH is enabled, the password is available on account

## Basics

### Architecture Overview

The PyRpiCamController follows a modular, event-driven architecture:

```
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

* **Cam State**: Captures images at configured intervals
* **Stream State**: Provides real-time video streaming  
* **Post State**: Handles image processing and publishing

### Configuration Philosophy

* **Single Source of Truth**: JSON schema defines all settings
* **Multi-Interface Access**: Web GUI, API, and file-based configuration
* **Runtime Updates**: Settings changes apply without restart where possible

### Hardware Abstraction

* **Camera Interface**: Pluggable camera modules (PiCam3, PiCamHQ)
* **IO Control**: PWM lighting, RGB status indicators
* **Connectivity**: WiFi management with fallback access point

