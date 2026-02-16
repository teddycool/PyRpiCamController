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
├── Settings/
│   ├── settings_schema.json       # Single source of truth - defines all settings
│   ├── settings_manager.py        # Python interface for code access
│   ├── user_settings.json         # User customizations (overrides defaults)
│   ├── demo_settings.py           # Demonstration script
│   └── add_setting_levels.py      # Schema categorization tool
└── WebGui/                        # Web interface
    ├── web_app.py                 # Flask web application
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

## File Locations

### Schema Files

- `Settings/settings_schema.json`: Master schema (version controlled)
- `Settings/user_settings.json`: User overrides (gitignored/user-specific)

### User Settings Persistence

User changes are saved to `Settings/user_settings.json` and automatically override defaults from the schema. This allows:

- Version control of default settings
- User-specific customizations without modifying defaults
- Easy reset to defaults by deleting Settings/user_settings.json