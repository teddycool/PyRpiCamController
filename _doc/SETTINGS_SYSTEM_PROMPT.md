# PyRpiCamController - Settings System Architecture & Flow Prompt

## Overview
Create a comprehensive diagram showing the complete settings system architecture and data flow timeline in PyRpiCamController. This should illustrate both the structure and the chronological flow from schema definition through web GUI interaction to code consumption.

## Settings System Components

### 1. Core Architecture Components

**settings_schema.json** - Master Schema (Single Source of Truth)
```json
{
  "schema_version": "1.0",
  "settings": {
    "SettingName": {
      "value": "default_value",           // Default value
      "type": "text|int|float|bool|enum|tuple",
      "min": 0, "max": 100,              // Validation constraints
      "options": ["opt1", "opt2"],       // Enum options
      "readonly": false,                 // Code-only modification
      "web_editable": true,              // Can be changed via web GUI
      "level": "basic|advanced",         // User experience level
      "ui": {
        "name": "Display Name (Swedish)", // Human-readable name
        "section": "Kamera|System|Vision|Stream", // Grouping
        "description": "User help text",  // Tooltip/description
        "level": "basic|advanced"         // UI complexity level
      }
    }
  }
}
```

**settings_manager.py** - Central Management Class
```python
class SettingsManager:
    + load_schema()                    // Load master schema
    + load_user_settings()             // Load user overrides
    + save_user_settings()             // Persist changes
    + get(path, default=None)          // Read setting value
    + set(path, value, save=True)      // Write setting value
    + get_ui_schema()                  // Extract UI metadata
    + get_web_editable_schema()        // Filter editable settings
    + _validate_value()                // Type & range validation
```

**user_settings.json** - User Customizations (Generated/Persisted)
```json
{
  "Mode": "Stream",                    // Override default "Cam"
  "Cam.timeslot": 60,                 // Override default 15
  "LogLevel": "info"                  // Override default "debug"
}
```

### 2. Web GUI Components

**web_app.py** - Flask Web Application
```python
@app.route("/")                       // Main settings form
@app.route("/api/settings", methods=["POST"])  // AJAX updates
@app.route("/api/settings/<path>")    // REST API

Key Functions:
+ index(level='basic')                // Render form by level
+ update_settings()                   // Process form submissions
+ validate_and_save()                 // Server-side validation
```

**settings_form.html** - Dynamic Web Interface
```html
<!-- Tab System -->
<div class="tabs">
  <a href="/?level=basic">Grundinställningar</a>
  <a href="/?level=advanced">Avancerade inställningar</a>
</div>

<!-- Section-based Organization -->
{% for section_name, section_fields in grouped_schema.items() %}
<div class="section">
  <h2>{{ section_name }}</h2>
  <!-- Auto-generated form controls based on schema -->
  {% for field_path, field_info in section_fields %}
    <!-- Dynamic input types: checkbox, select, text, number -->
  {% endfor %}
</div>
{% endfor %}
```

### 3. CamController Integration Points

**All CamController Components Access Settings Via:**
```python
from Settings.settings_manager import settings_manager

# Read operations (most common)
mode = settings_manager.get("Mode")
resolution = settings_manager.get("Cam.resolution")
timeslot = settings_manager.get("Cam.timeslot", 15)

# Write operations (rare - usually via web GUI)
settings_manager.set("LogLevel", "DEBUG")
```

## Complete Data Flow Timeline

### Phase 1: Schema Definition & Setup
```
1. Developer defines setting in settings_schema.json
   ├── Set default value, type, constraints
   ├── Define UI metadata (name, section, description)
   ├── Set access levels (basic/advanced, web_editable)
   └── Add validation rules (min/max, options)

2. settings_manager.py loads schema at startup
   ├── Parse JSON schema into internal structures
   ├── Validate schema integrity
   ├── Create default value lookup tables
   └── Build UI metadata maps

3. user_settings.json loaded (if exists)
   ├── Override default values with user customizations
   ├── Validate user values against schema
   └── Merge with defaults for complete settings view
```

### Phase 2: Web GUI Rendering & Interaction
```
4. User accesses web interface (http://device:8000)
   ├── Flask app calls settings_manager.get_web_editable_schema()
   ├── Filter settings by level (basic/advanced)
   ├── Group settings by section (Kamera, System, Vision, Stream)
   └── Inject current values from settings_manager.get(field)

5. Dynamic form generation in settings_form.html
   ├── Swedish language interface
   ├── Automatic input type selection:
   │   ├── bool → checkbox
   │   ├── enum → select dropdown
   │   ├── int/float → number input with min/max
   │   ├── text → text input
   │   └── tuple → specialized inputs
   ├── Real-time validation feedback
   ├── Read-only field handling
   └── Responsive section-based layout

6. User interaction & form submission
   ├── Client-side validation (HTML5 + JavaScript)
   ├── AJAX form submission to /api/settings
   ├── Server-side validation in web_app.py
   ├── Success/error feedback to user
   └── Live preview of changes (optional)
```

### Phase 3: Settings Persistence & Validation
```
7. Server processes form submission
   ├── Extract field values from POST data
   ├── Validate against schema constraints:
   │   ├── Type validation (int/float/bool conversion)
   │   ├── Range validation (min/max bounds)
   │   ├── Enum validation (valid options)
   │   └── Custom validation rules
   ├── Update internal settings state
   └── Persist changes to user_settings.json

8. Settings persistence & conflict resolution
   ├── Load current user_settings.json
   ├── Merge new changes with existing overrides
   ├── Write updated user_settings.json atomically
   ├── Handle file I/O errors gracefully
   └── Maintain backup of previous settings
```

### Phase 4: CamController Consumption
```
9. CamController components read settings
   ├── settings_manager.get() called throughout code
   ├── Dot notation path resolution (e.g., "Cam.timeslot")
   ├── Fallback to schema defaults if not in user_settings
   ├── Type conversion & validation on read
   └── Optional caching for performance

10. Runtime settings usage examples:
    ├── MainLoop.py: Mode selection for state transitions
    ├── PostState.py: Camera settings, publisher config
    ├── Camera classes: Resolution, exposure, timeslot
    ├── Publishers: URL endpoints, API keys, enable flags
    ├── Vision pipeline: Crop coordinates, motion thresholds
    └── Hardware I/O: GPIO pins, brightness levels

11. Dynamic settings reloading (if implemented)
    ├── File system watching for user_settings.json changes
    ├── Settings validation on reload
    ├── Component notification of setting changes
    ├── Graceful state transitions (e.g., Mode changes)
    └── Error handling for invalid runtime changes
```

## Architectural Patterns & Relationships

### Single Source of Truth Pattern
```
settings_schema.json (Master)
    ↓ (loaded by)
settings_manager.py (Controller)
    ↓ (provides interface to)
┌─────────────────┬─────────────────┐
│   Web GUI       │  CamController  │
│   Components    │   Components    │
└─────────────────┴─────────────────┘
```

### Data Flow Relationships
```
Schema Definition → Runtime Loading → Web Rendering → User Interaction 
       ↓               ↓                ↓               ↓
   Developer      settings_manager   web_app.py    User Browser
   (JSON file)    (Python class)    (Flask routes) (HTML forms)
                                                        ↓
Settings Persistence ← Validation ← Form Submission ←──┘
        ↓                ↓              ↓
  user_settings.json  web_app.py   HTTP POST
                                        ↓
CamController Usage ←──── settings_manager.get() ←──────┘
        ↓                      ↓
  All Components        Real-time Access
```

### Level-based Organization
```
Settings Schema
├── Level: "basic" (User-friendly, common settings)
│   ├── Mode (Cam/Stream)
│   ├── Cam.timeslot (Image interval)
│   ├── Cam.resolution (Image size)
│   ├── Cam.publishers.file.publish (Save to file)
│   └── LogToFile (Enable logging)
├── Level: "advanced" (Technical, expert settings)
│   ├── OTA configuration
│   ├── Motion detection parameters
│   ├── Vision processing settings
│   ├── Network timeouts
│   └── Hardware GPIO configurations
└── web_editable: false (Code-only settings)
    ├── Version numbers
    ├── Installation paths
    ├── System service names
    └── Internal state variables
```

### Section-based Grouping
```
UI Sections (Swedish Interface):
├── "System" - Core operation mode, OTA, logging
├── "Kamera" - Image capture, publishing, timing
├── "Stream" - Video streaming configuration
├── "Vision" - Image processing, motion detection
├── "Hardware" - GPIO, sensors, display
└── "Network" - Connectivity, timeouts, URLs
```

## Key Integration Points

### Settings Manager Integration
Every CamController component imports and uses settings_manager:
```python
# Common pattern across all modules:
from Settings.settings_manager import settings_manager

# In MainLoop.py
mode = settings_manager.get("Mode", "Cam")

# In PostState.py  
timeslot = settings_manager.get("Cam.timeslot")
publishers = settings_manager.get("Cam.publishers")

# In Camera classes
resolution = settings_manager.get("Cam.resolution") 
brightness = settings_manager.get("Cam.brightness")
```

### Web GUI Auto-Generation
The web interface dynamically builds forms based on schema:
```python
# In web_app.py
ui_schema = settings_manager.get_web_editable_schema()
for field, schema_info in ui_schema.items():
    # Auto-generate appropriate input type
    if schema_info['type'] == 'bool':
        render_checkbox(field, schema_info)
    elif schema_info['type'] == 'enum':
        render_select(field, schema_info['options'])
    # ... etc
```

### Validation Pipeline
Multi-layer validation ensures data integrity:
```
1. Client-side (HTML5): Basic type/range validation
2. Server-side (Flask): Schema constraint validation  
3. Runtime (settings_manager): Type conversion & bounds checking
4. Component-level: Domain-specific validation
```

## Extension Points

### Adding New Settings
1. **Define in schema**: Add to settings_schema.json with metadata
2. **Auto-generation**: Web GUI automatically includes new setting
3. **Code access**: Use settings_manager.get("new.setting") in code
4. **Validation**: Schema constraints automatically enforced

### New Setting Types
1. **Extend schema**: Add new type definition to schema
2. **Update manager**: Add validation logic to settings_manager.py
3. **Enhance GUI**: Add form control rendering to settings_form.html
4. **Document**: Update user guides and examples

### Multi-language Support
1. **Schema enhancement**: Add locale-specific UI metadata
2. **Template updates**: Support multiple language templates
3. **Manager extension**: Locale-aware schema loading
4. **User preference**: Language selection persistence

## Visual Layout Suggestions

### Top-to-Bottom Timeline Flow
1. **Development Phase**: Schema definition in JSON
2. **Startup Phase**: Loading and validation by settings_manager
3. **User Interface**: Web GUI generation and rendering
4. **User Interaction**: Form manipulation and submission
5. **Persistence**: Validation and saving to user_settings.json
6. **Runtime Usage**: CamController component consumption

### Left-to-Right Architecture
1. **Schema Layer**: JSON schema definition
2. **Management Layer**: Python settings_manager class
3. **Interface Layer**: Flask web application
4. **Presentation Layer**: HTML/CSS/JS user interface
5. **Application Layer**: CamController component usage

### Color Coding
- **Blue**: Schema and data structures
- **Green**: Python backend components  
- **Orange**: Web interface components
- **Purple**: User interaction flows
- **Gray**: File system and persistence

This diagram should serve as a complete reference for understanding:
- How settings flow from definition to usage
- Where to make changes for new settings
- The validation and persistence mechanisms
- The relationship between web GUI and code access
- Extension points for new functionality

Target audience: Developers working with the settings system, web interface, or needing to understand the configuration flow.