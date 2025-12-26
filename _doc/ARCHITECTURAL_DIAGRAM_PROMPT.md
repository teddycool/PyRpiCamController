# PyRpiCamController - CamController Architecture Diagram Prompt

## Overview
Create a comprehensive architectural diagram showing the structure, inheritance, and relationships of the PyRpiCamController's CamController module. This diagram should help programmers quickly understand the codebase structure and relationships.

## Key Components to Include

### 1. Entry Point & Main Control Flow
- **Main.py** - Application entry point, logging setup, CPU serial detection
- **MainLoop.py** - Core execution loop, GPIO initialization, state management
- **hwconfig.py** - Hardware configuration factory

### 2. State Machine Pattern (Core Architecture)
Show the State Pattern implementation with:

**BaseState.py** (Abstract Base Class)
```
+ initialize()
+ update(context)
+ dispose()
```

**Concrete States:**
- **InitState** - WiFi connection checking, system initialization
- **PostState** - Image capture, processing, publishing mode
- **StreamState** - Video streaming and real-time preview

**State Transitions:**
- InitState → PostState (when WiFi connected and Mode="Cam")
- InitState → StreamState (when WiFi connected and Mode="Stream")
- PostState ↔ StreamState (based on Mode setting changes)

### 3. Camera Abstraction Layer (Template Method Pattern)
**CamBase.py** (Abstract Base Class)
```
+ initialize()
+ update(context)
+ startStreaming()
+ iResSupported(res)
+ vResSupported(res)
- _currentimg: numpy.array
- _currentMetaData: dict
- _supportedImagesResolutions: list
- _supportedVideoResolutions: list
```

**Concrete Camera Implementations:**
- **PiCam3** - Raspberry Pi Camera v3 with picamera2/libcamera
- **PiCamHQ** - Raspberry Pi HQ Camera with advanced features  
- **WebCam** - USB webcam support with OpenCV

**Factory Method:**
- `getCam(camtype)` - Factory function returning appropriate camera instance

### 4. Publisher Strategy Pattern
**PublisherBase.py** (Abstract Base Class)
```
+ initialize(settings)
+ publish(jpgimagedata, metadata)
```

**Concrete Publishers:**
- **FilePublisher** - Local file system with Samba sharing
- **HttpPublisher** - HTTP/HTTPS remote server upload

### 5. Vision Processing Pipeline
**ProcessorBase.py** (Abstract Base Class)
```
+ process(image, metadata): (processed_image, enriched_metadata)
+ initialize(settings)
```

**ImageProcessor** - Pipeline coordinator managing multiple processors

**Concrete Processors:**
- **CropProcessor** - Image cropping with coordinate validation
- **MotionDetectionProcessor** - Motion detection and area highlighting

### 6. Hardware I/O Layer
- **Display.py** - LED status display control
- **Light.py** - LED strip/lightbox control
- **Tempmonitor.py** - Temperature monitoring

### 7. Connectivity & Utilities
- **WiFi.py** - Network connection management
- **cpuserial.py** - CPU serial number utilities
- **ModernStreamingServer.py** - HTTP video streaming server

### 8. Settings Integration
**settings_manager.py** - Unified settings management
```
+ get(key, default=None)
+ set(key, value)
+ load_schema()
+ load_user_settings()
+ save()
```

Show how all components access settings through this central manager.

## Relationships to Highlight

### Inheritance Hierarchies
1. **BaseState** → {InitState, PostState, StreamState}
2. **CamBase** → {PiCam3, PiCamHQ, WebCam}
3. **PublisherBase** → {FilePublisher, HttpPublisher}
4. **ProcessorBase** → {CropProcessor, MotionDetectionProcessor}

### Composition Relationships
1. **MainLoop** contains **BaseState** (current state)
2. **PostState** contains **CamBase** instance (camera)
3. **PostState** contains multiple **PublisherBase** instances
4. **PostState** contains **ImageProcessor** (vision pipeline)
5. **ImageProcessor** contains multiple **ProcessorBase** instances

### Dependencies & Data Flow
1. **Main.py** → **MainLoop.py** → **State Machine**
2. **All Components** → **settings_manager** (unified settings access)
3. **PostState** → **Camera** → **Vision Pipeline** → **Publishers**
4. **StreamState** → **Camera** → **StreamingServer**
5. **InitState** → **WiFi** → **State Transition**

### Configuration Flow
1. **hwconfig.py** defines hardware capabilities
2. **settings_manager** loads schema and user settings
3. **States** read settings for initialization
4. **Publishers** configure based on settings["Cam"]["publishers"]
5. **Vision pipeline** configures processors based on settings

## Visual Layout Suggestions

### Top-to-Bottom Layers:
1. **Entry Point** (Main.py)
2. **Control Layer** (MainLoop.py, settings_manager)
3. **State Machine** (BaseState hierarchy)
4. **Business Logic** (Camera, Vision, Publishers)
5. **Hardware I/O** (Display, Light, Temp, WiFi)

### Color Coding:
- **Blue**: Abstract base classes
- **Green**: Concrete implementations
- **Orange**: State machine components
- **Purple**: Settings and configuration
- **Gray**: Hardware I/O and utilities

### Connection Types:
- **Solid arrows**: Inheritance (is-a)
- **Dashed arrows**: Composition (has-a)
- **Dotted arrows**: Dependency/usage (uses)
- **Bold arrows**: Main data/control flow

## Code Modules Structure to Show
```
CamController/
├── Main.py                  # Entry point
├── MainLoop.py             # Core loop & state management
├── hwconfig.py            # Hardware configuration
├── CamStates/             # State Pattern
│   ├── BaseState.py       # Abstract base
│   ├── InitState.py       # Initialization state
│   ├── PostState.py       # Capture/publish state
│   └── StreamState.py     # Streaming state
├── Cam/                   # Camera Abstraction
│   ├── CamBase.py         # Abstract camera
│   ├── PiCam3.py          # Pi Camera v3
│   ├── PiCamHQ.py         # Pi HQ Camera
│   └── WebCam.py          # USB webcam
├── Publishers/            # Strategy Pattern
│   ├── PublisherBase.py   # Abstract publisher
│   ├── FilePublisher.py   # Local file output
│   └── HttpPublisher.py   # HTTP upload
├── Vision/                # Image processing
│   └── pipeline/
│       ├── ProcessorBase.py      # Abstract processor
│       ├── ImageProcessor.py     # Pipeline coordinator
│       └── processors/
│           ├── CropProcessor.py  # Image cropping
│           └── MotionDetectionProcessor.py
├── IO/                    # Hardware I/O
│   ├── Display.py         # LED display
│   ├── Light.py           # Light control
│   └── Tempmonitor.py     # Temperature
├── Connectivity/          # Network utilities
│   ├── WiFi.py            # WiFi management
│   └── cpuserial.py       # CPU serial
└── StreamingServer/       # Video streaming
    └── ModernStreamingServer.py
```

## Settings Integration Points
Show how each component accesses the unified settings:

- **MainLoop**: Mode selection, hardware enable flags
- **PostState**: Camera settings, publisher configuration, vision pipeline settings
- **StreamState**: Streaming resolution, server port
- **Publishers**: URLs, credentials, enable flags
- **Vision Pipeline**: Crop coordinates, motion detection thresholds
- **Hardware I/O**: GPIO pins, brightness levels

## Extension Points to Highlight
1. **New Camera Types**: Inherit from CamBase, implement required methods
2. **New Publishers**: Inherit from PublisherBase, add to settings schema
3. **New Vision Processors**: Inherit from ProcessorBase, add to pipeline
4. **New States**: Inherit from BaseState, add state transitions

This diagram should serve as a "roadmap" for developers to quickly understand:
- How components relate to each other
- Where to make changes for specific features
- The flow of data and control through the system
- How the settings system ties everything together
- Extension points for adding new functionality

Target audience: Programmers who need to understand, maintain, or extend the CamController codebase.