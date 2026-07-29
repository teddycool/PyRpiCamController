# Release Notes

## v1.2.0

YouTube Live release — performance metrics, async publishing, and Pi 3B+ optimizations.

### Highlights

- **YouTube performance metrics** — publish FPS, average/max publish time, frame counts, and drop rate are now exposed in the runtime status and Web GUI.
- **Async publishing pipeline** — the main capture path now queues frames and never blocks on FFmpeg stdin writes.
- **Lower-latency streaming defaults** — default bitrate reduced to 1500k and FFmpeg preset tuned for speed.
- **Throttling removed** — YouTube publishing no longer slows down when local viewers are connected.
- **OTA status hardening** — stale update checks no longer leave the Web GUI stuck in "checking".

### Validation

- Verified on Raspberry Pi 3B+ hardware.
- Confirmed YouTube publishing remains near 10 FPS with no frame skipping under normal load.
- Confirmed the Web GUI shows live YouTube publisher stats.

## v1.1.3

YouTube Live streaming support — runs alongside the local MJPEG stream.

### Highlights

- **YouTube Live publisher** (`CamController/Publishers/YouTubePublisher.py`): pushes the MJPEG camera stream to YouTube Live via FFmpeg + RTMPS.
  - Runs in a dedicated background thread alongside the existing local HTTP stream.
  - Exponential-backoff reconnect on FFmpeg exit (up to 5 retries, max 5-minute interval).
  - Automatically throttles frame rate when local clients are connected to reduce Pi load.
  - Silent AAC audio track added so YouTube accepts the stream.
- **Settings schema** — four new fields under `Cam.publishers.youtube`:
  - `publish` (bool toggle) — enable/disable YouTube Live.
  - `rtmps_url` (text) — RTMPS ingest URL from YouTube Studio.
  - `stream_key` (password) — stream key, never displayed in the Web GUI.
  - `bitrate` (enum: 1500k / 2500k / 4000k / 6000k) — video bitrate.
- All settings are editable in the Web GUI under **Kamera → Advanced**.
- `ffmpeg` system package already installed by `install-all-optimized.py`; no extra install step required.
- No changes to OTA, provisioning, or local streaming behaviour.

### Configuration

1. Set up a live event in YouTube Studio and copy the **RTMPS ingest URL** and **Stream key**.
2. In the Web GUI → Settings → Kamera (Advanced):
   - Enable **YouTube Live-strömning**.
   - Paste the RTMPS URL (e.g. `rtmps://a.rtmp.youtube.com/live2`).
   - Paste your stream key (stored securely, shown as `●●●●`).
   - Choose a bitrate matching your upload bandwidth.
3. Restart the CamController service (or apply via OTA).

### Validation

- Unit tests: `tests/unit/test_youtube_publisher.py`
- Integration tests: `tests/integration/test_youtube_streaming.py`

## v1.1.2

Production baseline release for secure provisioning, OTA, and release-based deployment.

### Highlights

- Fresh Pi provisioning from the dev machine using release tarballs.
- Secure OTA onboarding with key-based SSH and backend enrollment.
- OTA apply/check flow fixed so the installed version and GUI state update correctly.
- Camera and web services now wait for a real client network instead of starting in ComitUp AP mode.
- Unattended OS security updates enabled in the release flow.
- Removed legacy device registration/provisioning helpers that are no longer part of the supported flow.

### Validation

- Verified on fresh Raspberry Pi hardware.
- Confirmed provisioning, reboot, OTA apply, and service startup behavior.
- Confirmed the Web UI reflects the installed version after OTA.

## v1.0.6

OTA became production-ready and was validated on Raspberry Pi hardware.

### Highlights

- End-to-end OTA flow implemented and validated: check, download, checksum verify, backup, install, health verification, rollback path.
- Production OTA backend integrated at `https://www.sensorwebben.se/pycamota` with admin dashboard and device/release management.
- Web UI now supports OTA check/apply and dynamic changelog display from backend `release_notes`.
- Update daemon service hardening adjusted so CPU serial lookup works reliably (`/proc/cpuinfo` readable under systemd sandbox).

### Fixes included

- Fixed OTA authentication failures caused by `cpu_id=unknown` when `/proc/cpuinfo` was hidden by service sandboxing.
- Fixed API method handling compatibility for shared hosting in OTA backend admin endpoints.
- Improved package/checksum handling and update-manager error flow robustness.

### Upgrade notes

- Ensure the installed `camcontroller-update.service` matches repository version and run:
  - `sudo systemctl daemon-reload`
  - `sudo systemctl restart camcontroller-update.service`
- Register each device in OTA backend with matching CPU serial and API key.
- Upload release packages through OTA admin and set channel/status (`testing` / `stable`) before rollout.

### Validation summary

- Hardware validation completed for OTA path from older versions to `1.0.6`.
- Production endpoint check returns authorized responses with correct device identity.
- Device shows `1.0.6` in Web GUI after successful update.
- OTA update paths are present in the repository but are not supported for production use in this release.

### Known limitations

- Some advanced vision and integration features remain in active development.
- Update-related UI/API paths are considered experimental for now.

### Upgrade notes

- For existing setups, review Settings/settings_schema.json defaults before deployment.
- Use the shared SMB share name for client access.
- Validate camera type and mode after applying new settings.

### Verification summary (recommended before tag)

- Service startup and restart behavior validated.
- WiFi onboarding flow validated.
- Photo capture and stream mode validated.
- SMB read/write access validated from at least one client OS.
- Documentation links and examples validated.
