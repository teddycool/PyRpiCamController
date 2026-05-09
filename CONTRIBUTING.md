# Contributing Guidelines

Welcome! This document explains how to contribute code, documentation, and fixes to PyRpiCamController.

## For AI Coding Assistants (GitHub Copilot, Claude, etc.)

⚠️ **IMPORTANT:** Before making any code or documentation changes, review the development guidelines:

```
.dev-guidelines/README.md            ← Start here
  ├── DESIGN_PATTERNS.md            ← Patterns & coding style  
  ├── DOCUMENTATION_SYNC.md         ← When to update docs
  ├── SWEDISH_TRANSLATIONS.md       ← For _swe language pairs
  ├── INSTALLER_UPDATES.md          ← When to update tools/install-all-optimized.py
  ├── FILE_PERMISSIONS.md           ← Atomic writes & SMB
  ├── CODE_QUALITY.md               ← Testing & linting
  └── GIT_WORKFLOW.md               ← Commits & releases
```

**TL;DR for AI assistants:**
1. ✅ Use existing patterns: State Machine, Publisher, Factory, Pipeline (see DESIGN_PATTERNS.md)
2. ✅ Update docs when code changes (see DOCUMENTATION_SYNC.md)
3. ✅ If `.md` has `_swe` sibling, translate to Swedish too (see SWEDISH_TRANSLATIONS.md)
4. ✅ Update `tools/install-all-optimized.py` if code affects new installations (see INSTALLER_UPDATES.md)
5. ✅ Use atomic writes for any file persistence (see FILE_PERMISSIONS.md)
6. ✅ No backwards compatibility unless explicitly requested (break cleanly, update all callers)
7. ✅ Test before commit; run `pytest` (see CODE_QUALITY.md)
8. ✅ Commit messages must be clear with type prefix (feat:, fix:, docs:, etc. — see GIT_WORKFLOW.md)

**Key Patterns in This Codebase:**
- **Game Loop:** Main loop with state machine driving behavior
- **States:** InitState → PostState or StreamState (see `CamController/CamStates/`)
- **Lifecycle:** Classes use `__init__()` → `initialize(settings)` → `update()` → `cleanup()` → `dispose()`
- **Settings:** Use `settings_manager.get("path.to.setting")` or settings dict from `initialize()`
- **Publishers:** Publish images/data via FilePublisher, HttpPublisher, etc.
- **Hardware:** Abstracted in `CamController/IO/` and `CamController/Connectivity/`
- **Logging:** `logging.getLogger("cam.module.submodule")` with hierarchical names

**Installation Script:** Any code change that affects new installations MUST update `tools/install-all-optimized.py`:
- New Python package? Add to pip batch
- New systemd service? Enable + start in `setup_services()`
- New directory? Create + chmod in installer
- New config file? Copy + set permissions
- New startup script? Add to installer, make executable

See INSTALLER_UPDATES.md for detailed checklist.

## For Human Contributors

### Before Starting

1. **Read the development guidelines** in `.dev-guidelines/`
2. **Check open issues/PRs** (don't duplicate work)
3. **Discuss large changes** in an issue first

### Making Changes

1. **Follow the patterns** documented in DESIGN_PATTERNS.md
2. **Keep it simple** — avoid over-engineering
3. **Update relevant docs** (INSTALLATION.md, USER_GUIDE.md, TROUBLESHOOTING.md, etc.)
4. **If modifying a `.md` file with a `_swe` sibling, translate to Swedish**
5. **Update installer** (`tools/install-all-optimized.py`) if needed
6. **Test thoroughly** — run the test suite before committing
7. **Use atomic writes** for any file persistence
8. **Write clear commit messages** with type prefix (feat:, fix:, docs:, chore:, etc.)

### Testing

```bash
# Run unit tests
.venv/bin/python -m pytest tests/unit/ -v

# Run integration tests
.venv/bin/python -m pytest tests/integration/ -v

# Check for linting issues
.venv/bin/pylint CamController/ --disable=missing-docstring,too-many-instance-attributes
```

### Commit Message Format

```
<type>: <subject> [<scope>]

<body>

<footer>
```

**Types:**
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code restructuring (no behavior change)
- `test:` — Test additions/updates
- `chore:` — Build, config, tooling
- `perf:` — Performance improvement

**Example:**
```
feat: add motion detection processor to vision pipeline

Adds MotionDetectionProcessor class with configurable thresholds and 
motion area detection. Integrated into ImageProcessor pipeline.

Updated vision architecture docs and installer to include motion-events 
shared directory. Added smoke test for motion detection.

Fixes #123
Related-to: ARCHITECTURE.md, INSTALLATION.md
```

### Documentation Requirements

- If your change affects user behavior → update USER_GUIDE.md (+ USER_GUIDE_SWE.md)
- If installation changes → update INSTALLATION.md
- If new error scenarios → update TROUBLESHOOTING.md
- If architecture changes → update ARCHITECTURE.md
- If SMB/sharing changes → update SMB_FILE_SHARING.md
- New service/API → update ARCHITECTURE.md or README.md

### Do's and Don'ts

✅ **DO:**
- Keep methods focused and small (<50 lines)
- Use clear, descriptive names
- Log with context (not just "error")
- Write tests alongside code
- Break changes into small, reviewable commits
- Test on actual hardware if possible
- Update installer for new installations

❌ **DON'T:**
- Add backwards compatibility (break cleanly, update all callers)
- Use bare `except:` (catch specific exceptions)
- Create long procedural scripts (use classes + patterns)
- Hardcode paths (use Path, PROJECT_ROOT, or config)
- Modify shared state from callbacks (return values instead)
- Skip error handling for I/O operations
- Forget to update docs or installer

## Code Review Checklist

Before submitting or approving a PR:

- ✅ Follows design patterns (state machine, publisher, factory, etc.)
- ✅ Documentation updated (EN + SWE if applicable)
- ✅ Installer updated if needed (`tools/install-all-optimized.py`)
- ✅ Tests pass and new tests added
- ✅ Commit messages are clear and formatted correctly
- ✅ No breaking changes without update to all callers
- ✅ File writes use atomic pattern
- ✅ No secrets or credentials in code
- ✅ Logger names are hierarchical (`cam.module.submodule`)

## Getting Help

- **Architecture questions?** See ARCHITECTURE.md or `_doc/design.md`
- **Pattern examples?** See DESIGN_PATTERNS.md or look at existing classes in `CamController/CamStates/`
- **Installation questions?** See INSTALLER_UPDATES.md or INSTALLATION.md
- **Documentation questions?** See DOCUMENTATION_SYNC.md or SWEDISH_TRANSLATIONS.md
- **File permission issues?** See FILE_PERMISSIONS.md
- **Release process?** See GIT_WORKFLOW.md

## Questions?

If anything in these guidelines is unclear or contradicts the codebase, open an issue to discuss. The guidelines are living documents and evolve with the project.
