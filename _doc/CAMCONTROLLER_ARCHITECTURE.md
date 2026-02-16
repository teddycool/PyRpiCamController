# CamController Architecture and Implementation Guide

**Table of Contents**
- [Overview](#overview)
- [Architecture Overview](#architecture-overview)
- [Design Patterns](#design-patterns)
- [Core Components](#core-components)
- [State Machine](#state-machine)
- [Camera Abstraction Layer](#camera-abstraction-layer)
- [Publishing System](#publishing-system)
- [Vision Pipeline](#vision-pipeline)
- [Hardware Integration](#hardware-integration)
- [Configuration System](#configuration-system)
- [Extension Points](#extension-points)
- [Development Guidelines](#development-guidelines)

This document provides a comprehensive overview of the CamController architecture, design patterns, and implementation details for developers working with or extending the PyRpiCamController system.

## Overview

The CamController is the core component of the PyRpiCamController system, responsible for camera control, image capture, hardware management, and data publishing. It follows a modular, state-driven architecture designed for extensibility and maintainability.

### Design Philosophy

The CamController is built around several key principles:

- **Separation of Concerns** - Each module has a specific, well-defined responsibility
- **Extensibility** - New camera types, publishers, and hardware can be easily added
- **State Management** - Camera behavior is modeled as distinct states with clear transitions
- **Configuration-Driven** - Behavior is controlled through the unified settings system
- **Hardware Abstraction** - Hardware-specific code is isolated in dedicated modules

## Architecture Overview

### High-Level Structure

```
CamController/
├── Main.py              # Application entry point and logging setup
├── MainLoop.py          # Core execution loop and state management
├── hwconfig.py          # Hardware configuration definitions
├── LoggingSecure.py     # Secure logging utilities
├── Cam/                 # Camera abstraction layer
│   ├── CamBase.py       # Abstract base class for all cameras
│   ├── PiCam3.py        # Raspberry Pi Camera v3 implementation
│   ├── PiCamHQ.py       # Raspberry Pi HQ Camera implementation
│   └── WebCam.py        # USB webcam support
├── CamStates/           # State machine implementation
│   ├── BaseState.py     # Abstract base class for all states
│   ├── InitState.py     # Initialization and setup state
│   ├── PostState.py     # Image capture and publishing state
│   └── StreamState.py   # Video streaming state
├── IO/                  # Hardware input/output modules
│   ├── Display.py       # LED display control
│   ├── Light.py         # Light/LED strip control
│   └── Tempmonitor.py   # Temperature monitoring
├── Publishers/          # Image and data publishing
│   ├── PublisherBase.py # Abstract base class for publishers
│   ├── FilePublisher.py # Local file system publisher
│   └── HttpPublisher.py # HTTP/web service publisher
├── Connectivity/        # Network and connectivity
├── StreamingServer/     # Video streaming server
└── Vision/              # Computer vision and analysis
    ├── MotionDetector.py # Motion detection implementation
    └── pipeline/        # Image processing pipeline
        ├── ImageProcessor.py # Main image processing coordinator
        ├── ProcessorBase.py  # Abstract base for processors
        └── processors/ # Specific processing implementations
            ├── CropProcessor.py # Image cropping processor
            └── MotionDetectionProcessor.py # Motion detection processor
```

### Component Interaction

```
Main.py
    ↓
MainLoop.py ←→ Settings Manager (../Settings/)
    ↓
State Machine (InitState → PostState ↔ StreamState)
    ↓
Camera Abstraction (CamBase implementations)
    ↓
Publishers (File, HTTP)
    ↓
Hardware I/O (Display, Light, Temp)
    ↓
Vision Pipeline (Motion Detection, Image Processing)
```

## Design Patterns

### 1. State Pattern

The core camera behavior is implemented using the State pattern, allowing the system to change behavior based on its current operational mode.

#### Implementation

**BaseState.py** - Abstract base class defining the state interface:
```python
class BaseState(object):
    def __init__(self):
        return
    
    def initialize(self):
        self.lastUpdate = time.time()
        return
    
    def update(self, context):
        return
    
    def dispose(self):
        return
```

**Concrete States:**
- **InitState** - System initialization, camera setup, hardware configuration
- **PostState** - Image capture, processing, and publishing mode
- **StreamState** - Video streaming and real-time preview mode

#### Benefits
- Clear separation of different operational modes
- Easy to add new behaviors without modifying existing code
- State transitions are explicit and controllable
- Each state can have its own initialization and cleanup logic

### 2. Strategy Pattern (Publishers)

The publishing system uses the Strategy pattern to allow different methods of image distribution without changing the core capture logic.

#### Implementation

**PublisherBase.py** - Abstract publisher interface:
```python
class PublisherBase(object):
    def initialize(self, settings):
        raise NotImplementedError
    
    def publish(self, jpgimagedata, metadata):
        raise NotImplementedError
```

**Concrete Publishers:**
- **FilePublisher** - Saves images to local file system with Samba sharing
- **HttpPublisher** - Uploads images to web servers via HTTP POST

### 3. Abstract Factory Pattern (Camera Selection)

Camera types are created using factory methods, allowing runtime selection based on configuration.

```python
def create_camera(camera_type, settings):
    if camera_type == "PiCam3":
        return PiCam3(settings)
    elif camera_type == "PiCamHQ":
        return PiCamHQ(settings)
    elif camera_type == "WebCam":
        return WebCam(settings)
    else:
        raise ValueError(f"Unknown camera type: {camera_type}")
```

## Core Components

### MainLoop.py

The central orchestrator that:
- Manages the state machine
- Coordinates between components
- Handles timing and scheduling
- Manages configuration updates
- Implements the main update cycle

```python
class MainLoop:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.current_state = None
        self.camera = None
        self.publishers = []
        
    def run(self):
        while self.running:
            # Update current state
            self.current_state.update(self)
            
            # Check for mode changes
            self.check_mode_change()
            
            # Update hardware components
            self.update_hardware()
            
            # Sleep until next cycle
            time.sleep(self.update_interval)
```

### Settings Integration

The system is tightly integrated with the unified settings system:

```python
from Settings.settings_manager import SettingsManager

class CamComponent:
    def __init__(self):
        self.settings = SettingsManager()
        self.settings.register_callback('Cam.resolution', self.on_resolution_change)
        
    def on_resolution_change(self, new_value):
        """Handle resolution changes without restart"""
        self.camera.set_resolution(new_value)
```

## State Machine

### State Transitions

```
[Start] → InitState → {PostState, StreamState}
                         ↑           ↑
                         ↓           ↓
                      {PostState ←→ StreamState}
```

### State Responsibilities

#### InitState
- Hardware initialization
- Camera setup and testing
- Publisher initialization
- System health checks
- Transition to operational mode

#### PostState
- Periodic image capture
- Image processing pipeline
- Publisher distribution
- Motion detection
- Hardware control (lighting, display)

#### StreamState
- Real-time video streaming
- HTTP streaming server
- Live preview generation
- Minimal processing for performance

## Camera Abstraction Layer

### CamBase Abstract Interface

```python
class CamBase:
    def initialize(self, settings):
        """Initialize camera with settings"""
        pass
        
    def capture_image(self):
        """Capture a single image"""
        pass
        
    def start_preview(self):
        """Start live preview for streaming"""
        pass
        
    def set_resolution(self, resolution):
        """Change capture resolution"""
        pass
        
    def cleanup(self):
        """Clean up camera resources"""
        pass
```

### Camera Implementations

#### PiCam3.py
- Raspberry Pi Camera Module 3 support
- libcamera/picamera2 integration
- Hardware-specific optimizations
- Auto-focus and lens control

#### PiCamHQ.py
- High Quality Camera module support
- Studio-grade image quality
- Manual lens control
- Advanced exposure controls

## Publishing System

### Publisher Architecture

```python
class Publisher:
    def __init__(self, settings):
        self.settings = settings
        self.enabled = settings.get('publish', False)
        
    def publish(self, image_data, metadata):
        if not self.enabled:
            return
            
        try:
            self._do_publish(image_data, metadata)
        except Exception as e:
            self.logger.error(f"Publishing failed: {e}")
```

### Metadata System

Publishers receive rich metadata with each image:

```python
metadata = {
    'timestamp': datetime.now().isoformat(),
    'camera_settings': {...},
    'motion_detected': True/False,
    'processing_info': {...},
    'device_info': {...}
}
```

## Vision Pipeline

### Processing Architecture

```python
class ImageProcessor:
    def __init__(self, settings):
        self.processors = []
        self.load_processors(settings)
        
    def process(self, image, metadata):
        for processor in self.processors:
            if processor.enabled:
                image, metadata = processor.process(image, metadata)
        return image, metadata
```

### Available Processors
- **CropProcessor** - Image cropping and region selection
- **MotionDetectionProcessor** - Motion analysis and detection
- **Future processors** - Face detection, object recognition

## Hardware Integration

### Hardware Abstraction

Hardware components are abstracted through dedicated modules:

```python
class Light:
    def __init__(self, settings):
        self.pin = settings.get('Light.pin')
        self.brightness = settings.get('Light.value')
        
    def set_brightness(self, level):
        """Set LED brightness (0-100)"""
        pwm_value = int((level / 100) * 255)
        GPIO.output(self.pin, pwm_value)
```

### Supported Hardware
- **LED displays** - Status indicators
- **Light control** - PWM LED strips
- **Temperature monitoring** - CPU temperature
- **Future support** - External sensors, relays

## Configuration System

### Dynamic Configuration

The system supports runtime configuration changes:

```python
def on_setting_change(self, setting_path, new_value):
    """Handle setting changes without restart"""
    if setting_path == 'Cam.resolution':
        self.camera.set_resolution(new_value)
    elif setting_path == 'Cam.timeslot':
        self.update_capture_interval(new_value)
```

### Settings Categories
- **Camera settings** - Resolution, timing, exposure
- **Publishing settings** - Destinations, formats, metadata
- **Hardware settings** - GPIO pins, PWM values
- **System settings** - Logging, monitoring, updates

## Extension Points

### Adding New Camera Types

1. Create new camera class inheriting from `CamBase`
2. Implement required abstract methods
3. Add to camera factory function
4. Update settings schema for new camera options

### Adding New Publishers

1. Create publisher class inheriting from `PublisherBase`
2. Implement `initialize()` and `publish()` methods
3. Add configuration options to settings schema
4. Register in MainLoop publisher initialization

### Adding New Vision Processors

1. Create processor class inheriting from `ProcessorBase`
2. Implement `process()` method
3. Add configuration to Vision settings
4. Register in ImageProcessor pipeline

## Development Guidelines

### Code Organization
- Follow existing module structure
- Use abstract base classes for extensibility
- Implement proper error handling and logging
- Add comprehensive docstrings

### Testing Strategy
- Unit tests for individual components
- Integration tests for state transitions
- Hardware mocking for CI/CD
- Manual testing with real hardware

### Performance Considerations
- Minimize blocking operations in main loop
- Use appropriate buffering for image data
- Consider memory usage with large images
- Optimize critical paths (capture, processing)

### Error Handling
- Graceful degradation when hardware fails
- Retry mechanisms for network operations
- Comprehensive logging for debugging
- Recovery procedures for common failures

This architecture provides a robust, extensible foundation for camera control while maintaining clean separation of concerns and easy maintainability.