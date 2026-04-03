# Unified Settings System Setup Guide

**Table of Contents**
- [File Structure](#file-structure)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Configuration Sections](#configuration-sections)
- [File Locations](#file-locations)

This unified settings system solves the dual requirement:

- **Code Interface**: Easy programmatic access to settings from Python modules
- **Web GUI**: Dynamic form generation for user-friendly configuration

Both interfaces use the **same** underlying settings schema, ensuring consistency and eliminating duplication.

## File Structure

```
PyRpiCamController/
├── CamController/
│   └── hwconfig.py                # Hardware-specific configuration (camera type, GPIO)
├── Settings/
│   ├── settings_schema.json       # Single source of truth - defines all settings
│   ├── settings_manager.py        # Python interface for code access
│   ├── add_setting_levels.py      # Schema categorization tool
│   └── UNIFIED_SETTINGS_GUIDE.md # This documentation
└── WebGui/                        # Web interface
    ├── web_app.py                 # Flask web application
    ├── camcontroller-web.service  # Systemd service file
    └── templates/
        └── settings_form.html     # Auto-generated web form
```

## Quick Start
After installing the PyRpiCamcontroller, you can quickly test the unified settings system:
visit http://localhost:8000

**Web Interface Features:**
- 🇸🇪 **Swedish language interface** for easy local use
- 📋 **Basic/Advanced tabs** - organized by user experience level  
- 🔒 **Secure password fields** for API keys
- ✅ **Real-time validation** with helpful error messages

## Key Features

### Single Source of Truth

- `settings_schema.json` defines ALL settings once
- Includes default values, types, validation rules, and UI metadata
- Both code and web GUI use this same schema

### Web GUI Auto-Generation

- Forms automatically generated from schema
- Organized by sections
- Proper input types (text, number, checkbox, select)
- Validation feedback
- Read-only fields for system values

### Validation

- Type checking (int, float, bool, text, enum, tuple)
- Range validation (min/max values)
- Enum validation (predefined choices)
- Immediate feedback on invalid values

## Configuration Sections

The settings are organized into logical sections:

- **Logging**: Log levels, destinations, file rotation
- **Camera**: Resolution, framerate, image settings
- **Streaming**: Video streaming configuration
- **Motion Detection**: Motion detection parameters
- **Hardware**: Camera type, display, sensors
- **Publishing**: File and HTTP publishing options
- **Network**: WiFi configuration
- **System**: Timezone, startup options

### Notable Advanced Camera Setting

- `Cam.save_metadata_json` (bool, default: `false`, level: `advanced`)
  - Controls whether image metadata is saved/published as JSON.
  - Applied globally to all publisher types.
  - When `false`:
    - File publisher saves image files only (no companion `.json` metadata file).
    - HTTP publisher posts image data without metadata JSON payload.
  - When `true`:
    - File publisher saves both image and metadata `.json` file.
    - HTTP publisher includes metadata JSON in the request payload.

## File Locations

### Schema Files

- `Settings/settings_schema.json`: Master schema (version controlled)
- `Settings/user_settings.json`: User overrides (gitignored/user-specific)

### Hardware Configuration

**Important Separation**: The unified settings system handles all dynamic application settings, but hardware-specific configuration is kept separate:

- `CamController/hwconfig.py`: Hardware configuration (camera type, GPIO pins, board type)
  - These settings require physical access to modify
  - Changes require service restart
  - Examples: Camera chip type (`"PiCam3"` or `"PiCamHQ"`), GPIO pin assignments

**Why Separate?**
- Hardware settings are deployment-specific and rarely change
- Dynamic settings can be modified via web interface without restart
- Clear separation prevents accidental hardware misconfiguration

### User Settings Persistence

User changes are saved to `Settings/user_settings.json` and automatically override defaults from the schema. This allows:

- Version control of default settings
- User-specific customizations without modifying defaults
- Easy reset to defaults by deleting Settings/user_settings.json