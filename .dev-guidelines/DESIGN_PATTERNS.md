# Design Patterns & Coding Style Guide

**Principle:** New code should follow patterns and styles already established in the codebase. Prioritize simplicity and well-known patterns over complexity. Avoid backwards compatibility unless explicitly required.

## Patterns Used in PyRpiCamController

### 1. State Machine Pattern

**Where:** `CamController/CamStates/` (InitState, PostState, StreamState)

The application uses explicit state machines for different operational modes. Each state is a distinct class inheriting from `BaseState`.

```python
from CamStates import BaseState

class MyNewState(BaseState.BaseState):
    def __init__(self):
        super(MyNewState, self).__init__()
        return
    
    def initialize(self, settings):
        """Called when entering state. Settings dict passed in."""
        logger.info("MyNewState initialize...")
        self._resource = initialize_resource(settings)
        return
    
    def update(self, context):
        """Called each game loop iteration. context is MainLoop instance."""
        # Perform state-specific work
        self._resource.do_work()
        # Optionally transition to new state:
        # context.set_state(StateName.ANOTHER_STATE)
        return
    
    def cleanup(self):
        """Called before settings reload or state exit. Cleanup gracefully."""
        logger.info("MyNewState cleanup...")
        self._resource.stop()
        return
    
    def dispose(self):
        """Called on final shutdown. Same as cleanup for now."""
        return
```

**Key Rules:**
- Inherit from `BaseState.BaseState`
- Call `super().__init__()` in constructor
- Always implement `initialize(settings)`, `update(context)`, `cleanup()`, `dispose()`
- States are long-lived; use lifecycle methods, not constructors
- Pass settings to `initialize()`, not `__init__()`
- Use `context.set_state(StateName.X)` to transition
- Log with `logger.info()` on state changes; `logger.debug()` for details

### 2. Game Loop Pattern

**Where:** `CamController/Main.py` and `CamController/MainLoop.py`

The main execution follows a continuous game loop that repeatedly calls `update()` on the current state:

```python
class Main(object):
    def __init__(self):
        self._mainLoop = MainLoop.MainLoop()
    
    def run(self):
        logger.info("Starting mainloop initialize")
        self._mainLoop.initialize()
        running = True
        
        while running:
            try:
                self._mainLoop.update()
                time.sleep(0.5)  # Prevent busy-wait
            except KeyboardInterrupt:
                logger.info("User stopped mainloop")
                self._mainLoop.stop()
                running = False
            except Exception:
                logger.exception("Mainloop caught an exception but will continue")
```

**Key Rules:**
- Main loop: initialize → while loop → update → cleanup
- Catch exceptions broadly in main loop; don't crash
- Include sleep() to prevent excessive CPU (e.g., `time.sleep(0.5)`)
- Log exceptions with `logger.exception()` to include traceback
- Graceful shutdown on KeyboardInterrupt

### 3. Publisher Pattern

**Where:** `CamController/Publishers/` (FilePublisher, HttpPublisher, etc.)

Multiple publishers follow a common interface for publishing images/data:

```python
from .PublisherBase import PublisherBase

class MyPublisher(PublisherBase):
    def __init__(self):
        self.config_value = "default"
        logger.debug("Init MyPublisher")
    
    def initialize(self, settings):
        """Called once at startup. Load settings."""
        self.config_value = settings.get("MyPublisher", {}).get("config", "default")
        # Setup resources
        logger.info(f"MyPublisher initialized with {self.config_value}")
    
    def publish(self, image_path: Path, metadata: dict = None):
        """Publish image. Return True if successful."""
        try:
            # Use atomic write pattern for file creation
            # See FILE_PERMISSIONS.md for details
            logger.debug(f"Publishing {image_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish: {e}")
            return False
    
    def cleanup(self):
        """Called on reload or shutdown."""
        logger.info("MyPublisher cleanup...")
        # Close connections, release resources
```

**Key Rules:**
- Inherit from `PublisherBase`
- Implement `initialize(settings)`, `publish(image, metadata)`, `cleanup()`
- Return boolean from `publish()` to indicate success/failure
- All file writes must use atomic pattern (temp file → fsync → replace)
- Log operations with appropriate levels (debug for details, error for failures)

### 4. Factory Pattern (Camera Selection)

**Where:** `CamController/Cam/CamBase.py`

Camera-specific implementations are created via a factory function:

```python
class CamBase:
    @staticmethod
    def get_cam(cam_chip: str):
        """Factory method to get correct camera implementation."""
        if cam_chip == "PiCam3":
            return PiCam3.PiCam3()
        elif cam_chip == "PiCamHQ":
            return PiCamHQ.PiCamHQ()
        elif cam_chip == "WebCam":
            return WebCam.WebCam()
        else:
            logger.error(f"Unknown camera chip: {cam_chip}")
            return None
```

To add a new camera type:
1. Create class inheriting from `CamBase`
2. Add condition in `get_cam()` method
3. Update `INSTALLATION.md` and `ARCHITECTURE.md` with camera option
4. **Update `tools/install-all-optimized.py`** to set hardware config defaults

### 5. Pipeline/Processor Pattern

**Where:** `CamController/Vision/pipeline/` (ObjectDetectionProcessor, MotionDetectionProcessor, etc.)

Image processing uses a pluggable pipeline of processors:

```python
from Vision.pipeline.processors.ProcessorBase import ProcessorBase

class MyProcessor(ProcessorBase):
    def __init__(self):
        self._initialized = False
        self._results = {}
    
    def initialize(self, settings: Dict[str, Any]) -> None:
        """Initialize processor with settings. Handle errors gracefully."""
        try:
            logger.info("MyProcessor initializing...")
            self._config = settings.get('enabled', False)
            # Setup expensive resources
            self._initialized = True
            logger.info("MyProcessor initialized")
        except Exception as e:
            logger.error(f"MyProcessor init failed: {e}")
            # Initialize with safe defaults to prevent crashes
            self._initialized = False
            self._results = {}
    
    def process(self, frame, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process frame. Return results dictionary."""
        if not self._initialized:
            return {}
        
        try:
            # Do expensive work
            result = {'detection': True, 'confidence': 0.95}
            return result
        except Exception as e:
            logger.error(f"MyProcessor processing failed: {e}")
            return {}
```

**Key Rules:**
- Inherit from `ProcessorBase`
- Initialize with safe empty values on error (prevent cascade failures)
- `process()` should return a dict, empty dict on error
- Log initialization failures but don't crash
- Each processor independent; no shared state

### 6. Singleton Pattern (Settings Manager)

**Where:** `Settings/settings_manager.py`

Global settings instance accessed everywhere:

```python
from Settings.settings_manager import settings_manager

class MyClass:
    def initialize(self, settings):
        # Passed in explicitly
        name = settings.get("MyClass", {}).get("name", "default")
        
        # OR access global singleton (less preferred, but used in some places)
        name = settings_manager.get("MyClass.name")
```

**Key Rules:**
- Prefer settings passed explicitly to `initialize()`
- Use `settings_manager.get("path.to.setting")` for dot notation access
- Use `settings_manager.set()` or `settings_manager.save_user_settings()` to persist
- Settings manager provides single source of truth (see DOCUMENTATION_SYNC.md)
- All settings must be defined in `Settings/settings_schema.json`

### 7. Hardware Abstraction

**Where:** `CamController/IO/` (Light, Display, CpuTempMonitor, etc.)

Hardware-specific logic is isolated in abstraction layers:

```python
class MyHardwareDevice:
    def __init__(self, gpio, pin, config):
        """Initialize with GPIO library and config."""
        self._gpio = gpio
        self._pin = pin
        self._config = config
        self._initialized = False
    
    def start(self, level: float) -> None:
        """Start device at given level (0-100)."""
        try:
            self._gpio.setup(self._pin, self._gpio.OUT)
            self._gpio.PWM(self._pin, self._config.get("frequency", 1000))
            self._initialized = True
            self.set_level(level)
        except Exception as e:
            logger.error(f"Failed to start device: {e}")
    
    def set_level(self, level: float) -> None:
        """Update device level (0-100)."""
        if self._initialized:
            self._gpio.PWM(self._pin, int(level))
    
    def stop(self) -> None:
        """Stop device and cleanup."""
        try:
            if self._initialized:
                self._gpio.cleanup(self._pin)
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
```

**Key Rules:**
- Keep hardware-specific code isolated
- Accept GPIO/hardware interface in constructor, not as global
- Implement graceful degradation (device doesn't break if GPIO unavailable)
- Always include `try/except` around GPIO operations
- Document hardware dependencies in INSTALLATION.md

## Coding Style Conventions

### Class Structure

All classes follow this pattern:

```python
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("cam.component.subcomponent")

class MyComponent:
    """Short description of component."""
    
    def __init__(self):
        """Initialize object. Don't do expensive work here."""
        self._setting1 = "default"
        self._resource = None
        logger.debug("Init MyComponent")
    
    def initialize(self, settings: Dict[str, Any]) -> None:
        """Setup resources. Called once at startup.
        
        Args:
            settings: Configuration dictionary
        
        Raises:
            ValueError: If settings are invalid
        """
        logger.info("MyComponent initialize...")
        self._setting1 = settings.get("MyComponent", {}).get("setting1", "default")
        # Expensive setup here
        logger.info(f"MyComponent initialized: {self._setting1}")
    
    def update(self) -> None:
        """Perform work. Called repeatedly in game loop."""
        if self._resource is None:
            return
        # Do work
    
    def cleanup(self) -> None:
        """Release resources. Called before reload."""
        logger.info("MyComponent cleanup...")
        if self._resource:
            self._resource.close()
            self._resource = None
    
    def __del__(self):
        """Destructor. Call cleanup() to be safe."""
        try:
            self.cleanup()
        except Exception as e:
            logger.error(f"Cleanup in __del__ failed: {e}")
```

### Logger Names

Follow hierarchical naming based on package structure:

```python
# In CamController/Cam/PiCam3.py
logger = logging.getLogger("cam.cam.picam3")

# In CamController/CamStates/PostState.py
logger = logging.getLogger("cam.state.poststate")

# In CamController/Publishers/FilePublisher.py
logger = logging.getLogger("cam.publisher.file")

# In CamController/Vision/VisionManager.py
logger = logging.getLogger("cam.vision.manager")
```

Pattern: `"cam." + module_path_lowercase_with_dots`

### Type Hints

Use type hints on public methods and class attributes:

```python
from typing import Dict, List, Any, Optional, Tuple

class MyClass:
    def process(self, image: bytes, metadata: Optional[Dict] = None) -> Tuple[bool, str]:
        """Process image.
        
        Args:
            image: Raw image bytes
            metadata: Optional metadata dict
        
        Returns:
            (success: bool, message: str)
        """
        return True, "OK"
    
    def get_config(self) -> Dict[str, Any]:
        """Get component configuration."""
        return self._config
```

### Error Handling

All external operations (file I/O, network, GPIO) must be wrapped:

```python
import os

def save_config(self, path: Path, data: dict) -> bool:
    """Save config atomically. Return success."""
    try:
        # Atomic write pattern (see FILE_PERMISSIONS.md)
        temp_file = path.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, path)
        logger.info(f"Config saved: {path}")
        return True
    except IOError as e:
        logger.error(f"Failed to save config {path}: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        return False
```

## Principles for New Code

### 1. Simplicity First

- Use existing patterns rather than inventing new ones
- Prefer straightforward implementations over "clever" code
- If not in a game loop or state machine, question the design
- Avoid meta-programming (decorators, descriptors, metaclasses) unless necessary

### 2. Well-Known Patterns

Use only patterns already in the codebase:
- ✅ State Machine (InitState, PostState, StreamState)
- ✅ Publisher (File, HTTP)
- ✅ Factory (camera selection)
- ✅ Pipeline/Processor (vision processing)
- ✅ Hardware abstraction layers (IO, connectivity)
- ❌ Avoid: Observer pattern, Dependency Injection, Async/await, Decorators (unless simple)

### 3. No Backwards Compatibility by Default

If a feature needs to change:
- **Don't** add new parameters or methods to support old behavior
- **Do** update all callers simultaneously
- **Update** installation script and documentation together
- **Mention** breaking change in commit message and release notes

Example (DO NOT DO THIS):
```python
# BAD: Supporting old behavior
def initialize(self, settings, old_format=False):
    if old_format:
        # Handle legacy settings
    else:
        # New behavior
```

Example (DO THIS):
```python
# GOOD: Break cleanly, update everywhere
def initialize(self, settings):
    # New behavior only
```

Then update:
- All callers in the codebase
- `INSTALLATION.md` with migration notes
- Commit message: "BREAKING: Changed settings format from X to Y"

### 4. Installation Script Must Be Updated

**Rule:** Any change affecting new installations must update `tools/install-all-optimized.py`.

Examples of changes requiring installer updates:
- New Python package dependency → add to batch install
- New configuration file → add setup code
- New systemd service → add enable/start commands
- New hardware config option → add to config initialization
- New file permission requirement → add chown/chmod setup
- New shared directory structure → add mkdirs
- New service startup script → add chmod +x

```python
# In install-all-optimized.py

def setup_new_feature():
    """Setup new feature for new installations."""
    
    # Install packages
    log.log("INFO", "PACKAGES", "Installing new-feature-package...")
    packages = ["new-feature-package"]
    for pkg in packages:
        subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=True)
    
    # Create directories
    shared_dir = Path("/home/pi/shared/new-feature")
    shared_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["sudo", "chown", "-R", "pi:pi", str(shared_dir)], check=True)
    
    # Copy config
    config_file = PROJECT_ROOT / "config/new-feature-default.json"
    target_file = Path("/etc/camcontroller/new-feature.json")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(config_file, target_file)
    subprocess.run(["sudo", "chown", "pi:pi", str(target_file)], check=True)
```

### 5. Atomic Writes for Persistence

Any file write must use the atomic pattern to prevent corruption on power loss:

```python
import os
import tempfile
from pathlib import Path

def write_atomically(target: Path, content: bytes):
    """Write file atomically."""
    with tempfile.NamedTemporaryFile(
        dir=target.parent,
        delete=False,
        suffix='.tmp'
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
    
    temp_path = Path(tmp.name)
    os.replace(temp_path, target)
    
    # Sync parent directory
    parent_fd = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
```

See `FILE_PERMISSIONS.md` for complete atomic write guidelines.

## Common Anti-Patterns to Avoid

| Anti-Pattern | Why Avoid | Alternative |
|---|---|---|
| Global variables | Hard to test, implicit dependencies | Pass as parameters or use singleton pattern |
| Bare `except:` | Hides bugs, catches SystemExit | Use `except SpecificException:` |
| Circular imports | Imports fail mysteriously | Restructure modules; import at use-time if needed |
| Long methods (>50 lines) | Hard to test and understand | Extract methods with clear names |
| Late initialization | Dependencies unclear, bugs on module import | Initialize in `__init__()` or `initialize()` |
| Modifying shared state from callbacks | Race conditions, hard to debug | Return values instead; update in main loop |
| `os.system()` or shell=True | Security risk, hard to error-handle | Use `subprocess.run(..., check=True)` |
| Float comparisons with `==` | Floating point precision issues | Use `abs(a - b) < epsilon` |
| Mutable default arguments | Shared state across calls | Use `None` and create in function body |

## Documentation Requirements for New Code

When adding new classes/functions:

1. **Module docstring** — Describe what the module does
2. **Class docstring** — Purpose of the class
3. **Public method docstrings** — Args, returns, raises (Google style)
4. **Comments for "why"** — Explain non-obvious logic
5. **Inline comments** — Sparingly; code should be self-documenting

Example:
```python
class ImageProcessor:
    """Process images through configured pipeline of processors.
    
    The pipeline is initialized with a series of processor instances
    that are called in order on each frame. Results from each processor
    are accumulated and returned.
    """
    
    def add_processor(self, processor: ProcessorBase) -> None:
        """Add a processor to the pipeline.
        
        Args:
            processor: Processor instance to add
        
        Raises:
            TypeError: If processor does not inherit from ProcessorBase
        """
        if not isinstance(processor, ProcessorBase):
            raise TypeError("Processor must inherit from ProcessorBase")
        self._processors.append(processor)
    
    def process(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process frame through all processors in order.
        
        Args:
            frame: Input image frame (numpy array)
        
        Returns:
            Dictionary with processor results keyed by processor type
        """
        results = {}
        for proc in self._processors:
            results[type(proc).__name__] = proc.process(frame)
        return results
```
