# AI Development Instructions

This file contains instructions for AI coding assistants (GitHub Copilot, Claude, etc.) working on PyRpiCamController.

## Priority Rules for AI Assistants

**Before making ANY code or documentation changes, check these rules:**

### Rule 1: Design Patterns (MANDATORY)
New code must use patterns already in the codebase. **DO NOT invent new patterns.**

Allowed patterns:
- ✅ **State Machine** — Classes inheriting from `BaseState` with `initialize(settings)`, `update(context)`, `cleanup()`, `dispose()`
- ✅ **Publisher** — Classes inheriting from `PublisherBase` with `initialize(settings)`, `publish(image, metadata)`, `cleanup()`
- ✅ **Factory** — Static methods that return correct implementation (e.g., `CamBase.get_cam(chip_name)`)
- ✅ **Pipeline/Processor** — Classes with `initialize(settings)` and `process(frame)` returning results dict
- ✅ **Hardware Abstraction** — IO controllers with `__init__()`, `start()`, `update()`, `stop()`, `cleanup()`
- ✅ **Game Loop** — Main loop calling `initialize()` → `while: update()` → `cleanup()`

Forbidden patterns (unless pre-existing in codebase):
- ❌ Decorators (except simple ones)
- ❌ Async/await
- ❌ Metaclasses
- ❌ Dependency Injection frameworks
- ❌ Observer pattern (use game loop callbacks instead)
- ❌ Multiple inheritance
- ❌ Descriptor protocol

**Action:** See `.dev-guidelines/DESIGN_PATTERNS.md` for code examples.

### Rule 2: Documentation Sync (MANDATORY)
**Every code change must evaluate against documentation. If docs need updates, suggest them explicitly.**

When changing any of these:
- Feature behavior → Update USER_GUIDE.md (+ USER_GUIDE_SWE.md)
- Installation steps → Update INSTALLATION.md
- Error handling → Update TROUBLESHOOTING.md
- API/architecture → Update ARCHITECTURE.md
- SMB/sharing → Update SMB_FILE_SHARING.md
- Settings → Update UNIFIED_SETTINGS_GUIDE.md

**Action:** Format suggestions as:
```
### Suggested doc update: <FILENAME>

**Section:** <Where in doc>
**Reason:** <Why this doc needs updating>

**Proposed text:**
[Your suggested text here]
```

**Action:** See `.dev-guidelines/DOCUMENTATION_SYNC.md`.

### Rule 3: Swedish Translation (MANDATORY)
If a `.md` file has a `_*_swe.md` sibling, translate changes to Swedish too.

Current pairs:
- `USER_GUIDE.md` ↔ `USER_GUIDE_SWE.md`

Future pairs (if created):
- `INSTALLATION.md` ↔ `INSTALLATION_SWE.md`
- `TROUBLESHOOTING.md` ↔ `TROUBLESHOOTING_SWE.md`

**Action:** Use standardized Swedish terminology (see SWEDISH_TRANSLATIONS.md).
**Action:** See `.dev-guidelines/SWEDISH_TRANSLATIONS.md`.

### Rule 4: Installer Updates (MANDATORY)
**Any code change affecting FIRST-TIME installations must update `tools/install-all-optimized.py`.**

Update installer if you add:
- New Python package (add to pip batch)
- New system package (add to apt batch)
- New systemd service (enable + start)
- New directory or config file (create + chmod)
- New startup script (copy + make executable)
- New hardware option (prompt user in configure_hardware())

**Action:** See `.dev-guidelines/INSTALLER_UPDATES.md` for detailed checklist and examples.

**Verification:** Before committing, ask:
- ❓ Does this require packages/services/directories on new installs?
- ❓ Did I update `tools/install-all-optimized.py`?
- If YES to both → ✅ Good to commit

### Rule 5: Atomic Writes (MANDATORY)
Any file write must use atomic pattern to prevent corruption on power loss.

Pattern:
```python
import os, tempfile
from pathlib import Path

def write_atomically(target: Path, content: bytes):
    """Write file atomically."""
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.replace(Path(tmp.name), target)
    
    parent_fd = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
```

**Action:** See `.dev-guidelines/FILE_PERMISSIONS.md` for SMB permissions handling.

### Rule 6: No Backwards Compatibility (MANDATORY)
Unless explicitly asked, do NOT support both old and new behavior.

**BAD (don't do this):**
```python
def initialize(self, settings, legacy_format=False):
    if legacy_format:
        # Handle old behavior
    else:
        # New behavior
```

**GOOD (do this):**
```python
def initialize(self, settings):
    # New behavior only
    # Update all callers and installer
```

Then:
- Update ALL callers in codebase simultaneously
- Update `tools/install-all-optimized.py` if needed
- Update documentation
- Note in commit: "BREAKING: [change description]"

**Action:** See `.dev-guidelines/GIT_WORKFLOW.md` for commit format.

### Rule 7: Testing Required (MANDATORY)
All code changes must pass tests before commit.

```bash
# Run all tests
.venv/bin/python -m pytest tests/ -v

# Run specific test
.venv/bin/python -m pytest tests/unit/test_filepp#ublisher.py -v
```

**Action:** See `.dev-guidelines/CODE_QUALITY.md` for testing patterns and standards.

### Rule 8: Commit Message Format (MANDATORY)
All commits must use format: `<type>: <subject>`

Valid types:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `refactor:` — Code restructuring (no behavior change)
- `test:` — Test additions
- `chore:` — Build/config/tooling
- `perf:` — Performance improvement

**Example:**
```
feat: add motion detection processor (with Swedish guide update + installer update)

- Added MotionDetectionProcessor to vision.pipeline.processors
- Integrated into ImageProcessor pipeline
- Updated USER_GUIDE.md and USER_GUIDE_SWE.md with motion settings
- Updated installer to create motion-events directory
- See DESIGN_PATTERNS.md for Processor pattern

Fixes #123
```

**Action:** See `.dev-guidelines/GIT_WORKFLOW.md` for full commit message format.

## Execution Checklist for AI Assistants

Before committing your work:

1. **Patterns** — Does new code follow existing patterns? (DESIGN_PATTERNS.md)
2. **Documentation** — Did I update docs and suggest changes? (DOCUMENTATION_SYNC.md)
3. **Swedish** — If `.md` has `_swe` sibling, did I translate? (SWEDISH_TRANSLATIONS.md)
4. **Installer** — Does this affect new installations? If so, did I update tools/install-all-optimized.py? (INSTALLER_UPDATES.md)
5. **Atomic Writes** — Are all file writes using atomic pattern? (FILE_PERMISSIONS.md)
6. **Tests** — Do all tests pass? (.dev-guidelines/CODE_QUALITY.md)
7. **Commit Message** — Is it formatted correctly? (GIT_WORKFLOW.md)
8. **No Backwards Compat** — Did I break any existing code and update all callers?

## Code Style Quick Reference

### Logger Names
```python
logger = logging.getLogger("cam.module.submodule")
```

Hierarchy based on file path. Examples:
- `cam.cam.picam3` for `CamController/Cam/PiCam3.py`
- `cam.publisher.file` for `CamController/Publishers/FilePublisher.py`
- `cam.state.poststate` for `CamController/CamStates/PostState.py`

### Class Lifecycle
```python
class MyComponent:
    def __init__(self):
        """Initialize (lightweight setup only)."""
        self._setting = "default"
        logger.debug("Init MyComponent")
    
    def initialize(self, settings):
        """Setup resources (called at startup)."""
        logger.info("MyComponent initialize...")
        # Expensive setup here
    
    def update(self):
        """Called each frame/iteration."""
        # Do work
    
    def cleanup(self):
        """Release resources (called on reload)."""
        logger.info("MyComponent cleanup...")
    
    def dispose(self):
        """Final cleanup (same as cleanup currently)."""
```

### Settings Access
```python
# Preferred: passed explicitly
def initialize(self, settings):
    value = settings.get("MyClass", {}).get("key", "default")

# Alternative: global singleton (less preferred)
from Settings.settings_manager import settings_manager
value = settings_manager.get("MyClass.key")
```

### Error Handling
```python
try:
    result = perform_operation()
except SpecificError as e:
    logger.error(f"Failed: {e}")
    # Recovery or re-raise
except AnotherError as e:
    logger.exception("Unexpected error (with traceback)")
```

### Type Hints (on public methods)
```python
from typing import Dict, Any, Optional, Tuple

def process(self, image: bytes, metadata: Optional[Dict] = None) -> Tuple[bool, str]:
    """Process image. Returns (success, message)."""
    return True, "OK"
```

## File Structure Rules

- **Service code:** `CamController/`
- **Web interface:** `WebGui/`
- **Settings:** `Settings/` (schema + manager)
- **Testing:** `tests/` (unit, integration)
- **Installation:** `tools/` (install-all-optimized.py)
- **System files:** `Services/` (systemd, samba config, scripts)
- **Documentation:** `*.md` at project root (INSTALLATION.md, USER_GUIDE.md, etc.)
- **Developer guidelines:** `.dev-guidelines/` (this directory)
- **Packaging:** `build-scripts/`

## When to Ask for Manual Review

These situations require human review; don't proceed without confirmation:

- ❓ Adding new service or changing service architecture
- ❓ Changing database schema or settings storage format
- ❓ Breaking security model or permissions
- ❓ Major architectural refactor
- ❓ Uncertain about which pattern to use

**Action:** Update your task description and ask human for confirmation before implementing.

## Resources

- **DESIGN_PATTERNS.md** — Patterns with code examples
- **DOCUMENTATION_SYNC.md** — When/how to update docs
- **SWEDISH_TRANSLATIONS.md** — Swedish terminology and translation process
- **INSTALLER_UPDATES.md** — Installer update checklist
- **FILE_PERMISSIONS.md** — Atomic writes and SMB permissions
- **CODE_QUALITY.md** — Testing and linting standards
- **GIT_WORKFLOW.md** — Commits, versioning, releases
- **ARCHITECTURE.md** — System architecture (public docs)
- **INSTALLATION.md** — Setup instructions (public docs)
- **USER_GUIDE.md** — End-user documentation (public docs)

## Questions?

If guidelines are unclear or contradict actual code:
1. Re-check the files above
2. Open an issue for discussion
3. The guidelines are living documents; ambiguities should be clarified

**Last updated:** May 2026
**Applies to:** All development work on PyRpiCamController
