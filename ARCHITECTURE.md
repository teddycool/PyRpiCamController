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
- `Updates/*` — OTA manager/daemon, package install/rollback logic
- `backend/Updates/*` — OTA backend API/admin/dashboard and DB schema

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
- Stream server uses camera-native encoded MJPEG output for Raspberry Pi camera modules and serves MJPEG over HTTP.
- Stream framerate is client-aware: active framerate with connected viewers and reduced `idle_framerate` when no clients are connected.

## YouTube Live Publisher Architecture

- `CamController/Publishers/YouTubePublisher.py` streams MJPEG frames to YouTube Live through FFmpeg + RTMPS.
- The publisher uses an async queue so capture never blocks on FFmpeg stdin writes.
- Video encoding currently uses `libx264` with `ultrafast` and low-latency settings for reliability on Raspberry Pi.
- YouTube publish FPS is configurable in the schema and is currently limited to 5, 10, 15, or 20 FPS.
- The YouTube pipeline is independent from local MJPEG viewer count; local viewers no longer throttle publish FPS.
- Hardware H.264 acceleration can be revisited later, but the production path currently favors the known-stable software encoder path.

## Hardware IO and PWM Policy

- Light control uses PWM with backend priority:
  1. `pigpio` (preferred)
  2. `lgpio` (fallback)
  3. `RPi.GPIO` fallback is disabled
- If Light and Display pins conflict on PWM channel resources, Light is prioritized and Display output may be disabled.

## Service Topology

- `camcontroller.service` — main camera controller/runtime
- `camcontroller-web.service` — web settings UI
- `camcontroller-update.service` — OTA daemon and update orchestration
- `pigpiod.service` — required for preferred Light hardware PWM backend

## OTA Architecture

The OTA system is split between device-side update logic and backend release management.

### Device-side OTA

- `Updates/camcontroller_update_daemon.py` runs as `camcontroller-update.service` and performs scheduled checks.
- `Updates/camcontroller_update_manager.py` performs:
  - version check against backend
  - package download
  - SHA-256 verification
  - backup creation
  - package extraction/install
  - post-update health verification
  - rollback on failure
- Manual triggers are file-based:
  - `/tmp/ota_check_trigger`
  - `/tmp/ota_apply_trigger`

### Backend OTA

- `backend/Updates/api/ota_check.php` provides update metadata for devices.
- `backend/Updates/api/ota_report.php` receives install status reports.
- `backend/Updates/admin/*` provides release/device/log administration.
- Database schema (`backend/Updates/database/ota_schema_v2.sql`) stores admins, devices, releases, and OTA logs.

### Identity and Security

- Device identity uses CPU serial + API key.
- Service sandbox settings must allow CPU serial lookup via `/proc/cpuinfo`.
- Current service configuration keeps hardening while permitting serial access.

## Persistence And Observability

- Runtime status file: `/tmp/cam_runtime_status.json`
- Apply trigger file: `/tmp/cam_reload_settings.txt`
- Pending changes file: `/tmp/webgui_pending_changes.json`
- Logs via systemd journal and optional file logging

## Design Principles

- Keep runtime behavior predictable and restart-safe.
- Separate hardware configuration from web-editable settings.
- Prefer explicit, simple control paths over hidden implicit behavior.
