# Architecture Overview

PyRpiCamController is a service-based Raspberry Pi camera system with a state-machine core, schema-backed settings, and a web UI apply/restart workflow.

## High-Level Components

- `CamController/Main.py` — service entry point
- `CamController/MainLoop.py` — runtime loop, state transitions, status updates
- `CamController/CamStates/*` — state implementations (`InitState`, `PostState`, `StreamState`)
- `CamController/Cam/*` — camera abstraction and concrete camera implementations
- `CamController/StreamingServer/*` — stream server and frame pipeline
- `Settings/*` — schema and persistence (`settings_schema.json`, `user_settings.json`, manager)
- `WebGui/*` — web app and settings UI

## Runtime Model

1. Service starts `Main.py`.
2. `MainLoop` initializes sensors, display/light IO, and state objects.
3. Mode selects initial state:
   - `Cam` mode → `InitState`
   - `Stream` mode → `StreamState`
4. Main loop updates state and writes runtime status for Web UI polling.

## Settings Model

- Defaults come from `Settings/settings_schema.json`.
- User overrides are persisted to `Settings/user_settings.json`.
- Web edits are tracked as pending and applied via **Apply Changes & Restart Service**.
- Apply path is restart-only by policy.

## Camera and Stream Architecture

- `CamBase.get_cam()` selects the camera implementation (`PiCam2`, `PiCam3`, `PiCamHQ`, `WebCam`).
- Stream server captures frames from camera abstraction, encodes JPEG, and serves MJPEG.
- Target framerate pacing uses elapsed-time compensation.

## Hardware IO and PWM Policy

- Light control uses PWM with backend priority:
  1. `pigpio` (preferred)
  2. `lgpio` (fallback)
  3. `RPi.GPIO` fallback is disabled
- If Light and Display pins conflict on PWM channel resources, Light is prioritized and Display output may be disabled.

## Service Topology

- `camcontroller.service` — main camera controller/runtime
- `camcontroller-web.service` — web settings UI
- `pigpiod.service` — required for preferred Light hardware PWM backend

## Persistence And Observability

- Runtime status file: `/tmp/cam_runtime_status.json`
- Apply trigger file: `/tmp/cam_reload_settings.txt`
- Pending changes file: `/tmp/webgui_pending_changes.json`
- Logs via systemd journal and optional file logging

## Design Principles

- Keep runtime behavior predictable and restart-safe.
- Separate hardware configuration from web-editable settings.
- Prefer explicit, simple control paths over hidden implicit behavior.
