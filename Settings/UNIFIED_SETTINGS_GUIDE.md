# Unified Settings Guide

This guide describes the settings system used by PyRpiCamController.

## Files

- `Settings/settings_schema.json` — source of truth for defaults, types, ranges, and UI metadata
- `Settings/user_settings.json` — user overrides persisted from UI/API
- `Settings/settings_manager.py` — typed access, validation, and persistence

## How Values Resolve

1. Read user override from `user_settings.json` (if present).
2. Fall back to schema default from `settings_schema.json`.

## Web Edit Flow

1. User edits values in web UI.
2. Values are validated and persisted as pending/user overrides.
3. User clicks **Apply Changes & Restart Service**.
4. Service restart applies all changes.

This is a restart-only apply model.

## Hardware versus Web-Editable

- Hardware config: `CamController/hwconfig.py`
  - Camera type
  - GPIO pin assignments
  - Board-specific fixed wiring choices
- Web-editable settings: schema-defined fields exposed in UI/API

## Why Separation Exists

- Hardware settings are deployment-specific and infrequently changed.
- Runtime settings are frequently tuned by operators.
- Separation reduces accidental hardware misconfiguration.

## Common Paths Used in Code

- `settings_manager.get("Mode")`
- `settings_manager.get("Stream.framerate")`
- `settings_manager.get("Light")`
- `settings_manager.set(path, value, save=True)`

## Reset to Defaults

To reset user overrides, remove `Settings/user_settings.json` and restart services.

```bash
rm -f Settings/user_settings.json
sudo systemctl restart camcontroller.service camcontroller-web.service
```
