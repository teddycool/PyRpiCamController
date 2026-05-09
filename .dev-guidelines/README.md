# Development Guidelines for PyRpiCamController

This directory contains rulings and guidelines for future development work on this project. These guidelines are designed to maintain consistency, prevent regressions, and ensure comprehensive documentation and localization across the codebase.

## What's Inside

- **[DESIGN_PATTERNS.md](DESIGN_PATTERNS.md)** — Patterns and styles used in the codebase, principles for new code
- **[DOCUMENTATION_SYNC.md](DOCUMENTATION_SYNC.md)** — Rules for evaluating code changes against documentation and suggesting updates
- **[SWEDISH_TRANSLATIONS.md](SWEDISH_TRANSLATIONS.md)** — Guidelines for maintaining Swedish (_swe) document pairs
- **[CODE_QUALITY.md](CODE_QUALITY.md)** — Testing, linting, and code standards
- **[FILE_PERMISSIONS.md](FILE_PERMISSIONS.md)** — Hard-learned lessons about SMB, file ownership, and atomic writes
- **[INSTALLER_UPDATES.md](INSTALLER_UPDATES.md)** — When and how to update `tools/install-all-optimized.py` for new installations
- **[GIT_WORKFLOW.md](GIT_WORKFLOW.md)** — Commit messages, branching, and release processes

## Quick Reference

| Scenario | Rule |
|----------|------|
| New code/feature | Follow existing patterns (state machine, publisher, factory); simplicity first; see DESIGN_PATTERNS.md |
| New class method | Use lifecycle pattern: `__init__()` → `initialize(settings)` → `update()` → `cleanup()` |
| Code changes service behavior | Update `tools/install-all-optimized.py` for new installations; see INSTALLER_UPDATES.md |
| Edit a `.md` file | Check for `_swe` sibling; if exists, translate changes to Swedish |
| New code feature | Check and update relevant docs; suggest doc changes if needed |
| SMB/file operations | Use atomic writes (temp file → fsync → replace); ensure permissions via `_ensure_smb_permissions()` |
| Test before commit | Run relevant unit/integration tests; verify no regressions |
| Release candidate | Run smoke tests; verify docs are up-to-date |
| Logger name | Use hierarchical: `logging.getLogger("cam.module.submodule")` |
| No backwards compatibility | Break cleanly; update all callers together; update installer and docs |

## File Organization

Assets and guidelines:
- `.dev-guidelines/` — This directory (for coders/agents, not end users)
- `ARCHITECTURE.md` — Public technical overview
- `INSTALLATION.md`, `USER_GUIDE.md`, `USER_GUIDE_SWE.md` — Public docs
- `TROUBLESHOOTING.md`, `SMB_FILE_SHARING.md` — Public support docs
