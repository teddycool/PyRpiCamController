# System Instructions for AI Coding Assistants

**Read this first before making any changes to this repository.**

## Core Rules (MANDATORY)

This file serves as system-level instructions for any AI coding assistant working on PyRpiCamController. These rules must be followed for all code and documentation changes.

### 1️⃣ Read All Guidelines First

Before writing any code, documentation, or making configuration changes, read these files in this order:

1. **[CONTRIBUTING.md](CONTRIBUTING.md)** — Overview of contribution process
2. **[.dev-guidelines/AI_INSTRUCTIONS.md](.dev-guidelines/AI_INSTRUCTIONS.md)** — Specific instructions for AI assistants (⚠️ READ THIS)
3. **[.dev-guidelines/DESIGN_PATTERNS.md](.dev-guidelines/DESIGN_PATTERNS.md)** — Code patterns used in project
4. **[.dev-guidelines/INSTALLER_UPDATES.md](.dev-guidelines/INSTALLER_UPDATES.md)** — When to update installer
5. **[.dev-guidelines/DOCUMENTATION_SYNC.md](.dev-guidelines/DOCUMENTATION_SYNC.md)** — Documentation update rules
6. **[.dev-guidelines/SWEDISH_TRANSLATIONS.md](.dev-guidelines/SWEDISH_TRANSLATIONS.md)** — Swedish language pairs

### 2️⃣ Three Things You MUST Do

Every single time you make code or documentation changes:

1. **Check Documentation** — Does your code change require doc updates? (See DOCUMENTATION_SYNC.md)
2. **Check Installation** — Does your change affect new installations? If yes, update `tools/install-all-optimized.py` (See INSTALLER_UPDATES.md)
3. **Check Swedish** — If editing a `.md` file with a `_swe` sibling, translate to Swedish too (See SWEDISH_TRANSLATIONS.md)

### 3️⃣ Code Patterns

Only use patterns that already exist in the codebase: **State Machine**, **Publisher**, **Factory**, **Pipeline/Processor**, **Game Loop**, **Hardware Abstraction**

See [.dev-guidelines/DESIGN_PATTERNS.md](.dev-guidelines/DESIGN_PATTERNS.md) for code examples.

**Do NOT:**
- Create new pattern types
- Use decorators (except simple ones)
- Use async/await
- Use dependency injection
- Overly architect simple things

### 4️⃣ File Persistence Rules

**Every file write must use atomic pattern:** temp file → fsync → atomic replace.

```python
import os, tempfile
from pathlib import Path

with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
    tmp.write(content)
    tmp.flush()
    os.fsync(tmp.fileno())

os.replace(Path(tmp.name), target)
```

See [.dev-guidelines/FILE_PERMISSIONS.md](.dev-guidelines/FILE_PERMISSIONS.md).

### 5️⃣ No Backwards Compatibility

Unless explicitly asked, do NOT support old behavior. Break changes cleanly:
- Update ALL callers in codebase
- Update installer
- Update documentation
- Note as BREAKING in commit message

### 6️⃣ Testing Required

All changes must pass tests:

```bash
.venv/bin/python -m pytest tests/ -v
```

See [.dev-guidelines/CODE_QUALITY.md](.dev-guidelines/CODE_QUALITY.md).

### 7️⃣ Proper Commit Messages

Format: `<type>: <subject>`

Types: feat, fix, docs, refactor, test, chore, perf

Example:
```
feat: add motion detection processor (+ Swedish guide + installer)

- Added MotionDetectionProcessor to pipeline
- Updated USER_GUIDE.md and USER_GUIDE_SWE.md
- Updated installer for motion-events directory
- See DESIGN_PATTERNS.md for Processor pattern

Fixes #123
```

See [.dev-guidelines/GIT_WORKFLOW.md](.dev-guidelines/GIT_WORKFLOW.md).

## Pre-Commit Verification

Before committing, verify:

- ✅ Code follows existing patterns (DESIGN_PATTERNS.md)
- ✅ Documentation updated (DOCUMENTATION_SYNC.md)
- ✅ Swedish translations if applicable (SWEDISH_TRANSLATIONS.md)
- ✅ Installer updated if needed (INSTALLER_UPDATES.md)
- ✅ Tests passing (CODE_QUALITY.md)
- ✅ Commit message formatted correctly (GIT_WORKFLOW.md)
- ✅ File writes use atomic pattern (FILE_PERMISSIONS.md)
- ✅ Logger names hierarchical (`cam.module.submodule`)

## Key Files to Know

| File | Purpose |
|------|---------|
| `.dev-guidelines/` | All developer guidelines (7 markdown files) |
| `CONTRIBUTING.md` | Human-readable contribution guide |
| `pyproject.toml` | Project config + tool settings |
| `.vscode/extensions.json` | Recommended VS Code extensions |
| `ARCHITECTURE.md` | Technical architecture (public) |
| `INSTALLATION.md` | Setup guide (public) |
| `USER_GUIDE.md` | End-user guide (public) |
| `USER_GUIDE_SWE.md` | Swedish end-user guide (public) |
| `tools/install-all-optimized.py` | Installation script (UPDATE THIS!) |
| `Settings/settings_schema.json` | Settings definition (golden source) |

## Common Tasks & Which Guide to Check

| Task | See file |
|------|----------|
| Add new class/function | DESIGN_PATTERNS.md |
| Modify code behavior | DOCUMENTATION_SYNC.md + DESIGN_PATTERNS.md |
| Add new feature | DESIGN_PATTERNS.md + INSTALLER_UPDATES.md + DOCUMENTATION_SYNC.md |
| Change installation | INSTALLER_UPDATES.md |
| Write to disk | FILE_PERMISSIONS.md |
| Update docs | DOCUMENTATION_SYNC.md |
| Translate to Swedish | SWEDISH_TRANSLATIONS.md |
| Create tests | CODE_QUALITY.md |
| Make commit | GIT_WORKFLOW.md |

## Quick Reference: Logger Names

```python
# Hierarchical based on file path + lowercase
logging.getLogger("cam.cam.picam3")              # CamController/Cam/PiCam3.py
logging.getLogger("cam.publisher.file")          # CamController/Publishers/FilePublisher.py
logging.getLogger("cam.state.initstate")         # CamController/CamStates/InitState.py
logging.getLogger("cam.vision.manager")          # CamController/Vision/VisionManager.py
```

## Quick Reference: Class Lifecycle

```python
class MyComponent:
    def __init__(self):
        """Lightweight init only."""
        logger.debug("Init MyComponent")
    
    def initialize(self, settings):
        """Setup resources (called once at startup)."""
        logger.info("MyComponent initialize...")
    
    def update(self):
        """Perform work (called each iteration/frame)."""
        pass
    
    def cleanup(self):
        """Release resources (called on reload/shutdown)."""
        logger.info("MyComponent cleanup...")
    
    def dispose(self):
        """Final cleanup (same as cleanup currently)."""
```

## If You're Unsure

1. **Check the guidelines** — Your question is probably answered in `.dev-guidelines/`
2. **Look at existing code** — See how other classes implement the pattern
3. **Ask for clarification** — Open an issue or discussion
4. **Re-read AI_INSTRUCTIONS.md** — If still unsure, read the AI instructions again

## Important Notes

- These guidelines are **not suggestions** — they are **mandatory rules** for ensuring code quality and consistency
- Guidelines are stored in `.dev-guidelines/` (hidden from end users, for developers only)
- Existing codebase is the source of truth for patterns (follow what's already there)
- When in doubt, keep it simple and follow existing patterns
- Future AI assistants will read these guidelines before making changes

---

**Last Updated:** May 2026  
**Applies To:** All development work on PyRpiCamController  
**Questions?** See CONTRIBUTING.md or individual guideline files in `.dev-guidelines/`
