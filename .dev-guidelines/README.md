# Development Guidelines for PyRpiCamController

This directory contains project guidelines for contributors and coding agents. The goal is consistent architecture, safer changes, and synchronized documentation.

## Contents

- [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) — Core implementation patterns
- [DOCUMENTATION_SYNC.md](DOCUMENTATION_SYNC.md) — Rules for keeping docs in sync
- [SWEDISH_TRANSLATIONS.md](SWEDISH_TRANSLATIONS.md) — Swedish document update rules
- [CODE_QUALITY.md](CODE_QUALITY.md) — Testing and quality expectations
- [FILE_PERMISSIONS.md](FILE_PERMISSIONS.md) — SMB permissions and atomic write lessons
- [INSTALLER_UPDATES.md](INSTALLER_UPDATES.md) — Installer update checklist
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) — Branching, commits, and release workflow

## Quick Reference

- **New code/feature**: Follow existing patterns (state machine, publisher, factory) and keep solutions simple.
- **New class method**: Prefer lifecycle shape: `__init__()` → `initialize(settings)` → `update()` → `cleanup()`.
- **Service behavior changes**: Update installer behavior and related docs.
- **Markdown edits**: Check for Swedish sibling docs and update both when needed.
- **SMB/file writes**: Use atomic write pattern (`temp -> fsync -> replace`) and validate permissions.
- **Before commit**: Run relevant tests and verify no regressions.

## File Organization

- `.dev-guidelines/` — Internal contributor/agent guidance
- `ARCHITECTURE.md` — Public technical overview
- `INSTALLATION.md`, `USER_GUIDE.md`, `USER_GUIDE_SWE.md` — Public usage docs
- `TROUBLESHOOTING.md`, `SMB_FILE_SHARING.md` — Public support docs
