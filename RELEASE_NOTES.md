# Release Notes

This file is the canonical project changelog.

- Newest release is always at the top.
- Historical entries are kept below.
- Per-build notes are also generated in `dist/release-notes-<version>.md`.

## v1.5.11

Release date: 2026-08-23

### Highlights

- [Add release highlights]

### Validation

- [Add validation notes]

## v1.5.11

Release date: 2026-08-23

### Highlights

- Public follow-up release after `v1.5.6`.
- Internal `v1.5.7` was release-engineering and verification work; user-facing improvements are summarized here in `v1.5.8`.
- OTA observability and support documentation improvements:
  - Added a dedicated `OTA_DAEMON_GUIDE.md` with trigger paths, flow details, failure modes, and a filesystem/unit-sync decision tree.
  - Embedded full OTA workflow flowchart image in the guide.
  - Updated related docs (`ARCHITECTURE.md`, `INSTALLATION.md`, `TROUBLESHOOTING.md`) to align with current trigger paths and OTA behavior.
- Web GUI OTA/status improvements:
  - OTA update widget now surfaces release notes for the available update directly in the same panel.
  - Filesystem health signal parsing was hardened to avoid false positives from embedded OTA release-note payload lines in logs.
- OTA backend/admin hardening:
  - `api/ota/report` now accepts the status values emitted by current device update code, removing non-fatal 400 report noise.
  - `api/ota/check` and OTA Logs messaging were improved so “up to date” vs “update available” outcomes are clearer.
  - OTA admin dashboard release management now includes an edit action/modal for release channel/status updates (for testing-to-stable promotion flow).
- Metrics logging and architecture refactor:
  - Added dedicated structured metrics logging to `cam-metrics.log` (`cam.metrics` JSON events) with configurable file path/size/rotation and interval.
  - Added component-owned metrics contracts (`get_metrics`) across states, stream server, publishers, and camera backends.
  - Standardized camera metrics keys across camera types, while preserving backend-specific metrics under a dedicated `backend_specific` block (including PiCam3 autofocus metrics).
- Web GUI metrics observability:
  - Added a new **Metrics** tab with a fixed 24-hour window.
  - Added 3 widgets: temperature, CPU load, and storage free/used, each with missing-data gaps rendered as breaks.
  - Added historical mode and YouTubeLive transition indicators directly in each graph, including visible text labels (no hover dependency).
- Web GUI operational UX changes:
  - Removed the AWB top-header indicator.
  - Moved the three device action buttons (stop service, restart device, shutdown) to the top area under runtime header widgets.
  - Removed the **Tools** tab from navigation and routing.
- Docs tab improvement:
  - Added a GitHub quick action card linking directly to issue creation (`Report a problem` → `issues/new`).

### End-user summary

- You now get a dedicated **Metrics** tab showing the last 24 hours of:
  - camera/environment temperature,
  - CPU load,
  - storage usage (free/used).
- The graphs now show **when mode changed** (Cam/Stream) and **when YouTube Live state changed**, so it is easier to understand why temperatures or load changed.
- Device control buttons (**Stop Camera Service**, **Restart Camera**, **Shut Down Camera**) are now easier to access at the top of the page.
- The old **Tools** tab was removed to simplify navigation.
- In **Docs**, there is now a direct **Report a problem** link that opens a new GitHub issue form.

### Validation

- OTA apply path validated to `1.5.7`/`1.5.8` package level with successful checksum verification, service-health verification, and unit-sync handling.
- Admin dashboard release/device/log tabs verified after UI updates and script fixes.
- Web GUI metrics tab verified with 24-hour data rendering, mode/YouTube transition markers, and text labels in Firefox.
- Metrics payload and logging verified on target Pi (`192.168.1.140`), including storage fields (`free_bytes`, `used_bytes`, `total_bytes`) emitted from runtime snapshots.
- Deployed and restarted `camcontroller.service` and `camcontroller-web.service` on target Pi after branch updates; services confirmed active.

## v1.5.6

Release date: 2026-08-21

### Highlights

- [Add release highlights]

### Validation

- [Add validation notes]

## v1.5.5

Release date: 2026-08-20

### Highlights

- Public rollout release covering all improvements made after `v1.5.0`.
- Includes the internal `v1.5.1`–`v1.5.4` work (those versions were not publicly released).
- Better live stream quality and stability, especially on Raspberry Pi 3 + Pi Camera 3:
  - Improved MJPEG handling at higher resolutions.
  - Better stream behavior when running both local preview and YouTube Live in parallel.
  - Added safer defaults/guardrails for high-load stream combinations on Pi 3-class hardware.
- Better camera color control in stream mode:
  - White balance mode and AWB behavior are now configurable.
  - Added runtime AWB status visibility in the top status area.
- Improved Web GUI usability:
  - Added a dedicated **Tools** tab.
  - Moved device actions into Tools for clearer day-to-day operation.
- More reliable service control from the Web GUI:
  - Camera service stop/start now validates actual service state and returns clear errors if the requested state is not reached.
- More robust network/startup behavior:
  - Comitup/portal behavior now yields correctly to normal operation when a real wired/client network is available.
- OTA update flow improvements:
  - `camcontroller-web` is now restarted after OTA apply so GUI/backend changes become active immediately.

### Validation

- Release pipeline completed successfully for `v1.5.5`.
- Validated on Raspberry Pi target devices with service restart and runtime verification.
- Verified camera + web services active after deploy, including fixed network/startup behavior.


## v1.5.0

Release date: 2026-08-08

### Highlights

- Baseline public `1.5.x` release used as the starting point for subsequent operational, streaming, and UX improvements delivered in `v1.5.5`.

### Validation

- Baseline release validation completed at time of `v1.5.0` publication.

## v1.4.3

Release date: 2026-08-08

### Highlights

- Added **Docs tab** to the Web GUI with links to project markdown guides.
- Added secure docs API endpoints in web service:
  - `/api/docs/<doc_id>` for whitelisted markdown documents.
  - `/api/doc-assets/<path>` for safe image serving from `_doc/`.
- Added markdown rendering in the Web GUI docs viewer.
- Web service logging migrated to `journald` for Gunicorn access/error output.
- OTA update flow now applies changed service units automatically after successful update.

### Validation

- Web GUI compiles and starts.
- Docs tab tested with markdown content and linked images.
- `camcontroller-web.service` verified active after deployment restart.

## v1.4.2

Release date: 2026-08-06

### Highlights

- Reorganized Web GUI tabs:
  - Status tab as default view.
  - Stream status and OTA status moved into Status tab.
- Improved top-header runtime widgets across all tabs.
- Production provisioning enhancements:
  - Artifact backup to SMB by device hostname.
  - Include deployed settings, device SMB credentials, OTA key, release tarball + checksum.
  - Include install log in production artifact bundle.

### Validation

- Fresh-device install and production deploy validated.
- Backup artifacts verified in SMB destination.

## v1.4.1

Release date: 2026-08-05

### Highlights

- Improved provisioning and deployment workflow reliability.
- Added/expanded Web GUI operational logging.
- Included release/deploy fixes for production flow.

## v1.4.0

Release date: 2026-08-04

### Highlights

- Updated YouTube settings UX and level assignment.
- Release baseline updates for 1.4.x branch.

## v1.3.0

Release date: 2026-08-03

### Highlights

- Stable 1.3 baseline before 1.4 production hardening series.
- Release packaging and deployment flow alignment.

## v1.2.4

Release date: 2026-08-02

### Highlights

- Stream FPS behavior improved when YouTube Live is active.
- Release packaging fixes and reusable Pi smoke test improvements.

## v1.2.3

Release date: 2026-08-01

### Highlights

- Release manager update to auto-bump version in release pipeline.
- Patch-level fixes from code-review integration.

## v1.2.1

Web GUI polish release — clearer settings layout, configurable YouTube FPS, English UI labels, and refreshed documentation.

### Highlights

- **Settings UI reorganized** — the Web GUI now groups settings into clearer sections, including dedicated **YouTube Live** and **Updates (OTA)** areas.
- **Configurable YouTube FPS** — YouTube publish FPS can now be selected from `5`, `10`, `15`, or `20` in the Web GUI.
- **English-only Web GUI** — settings labels, section names, helper text, and related schema-backed descriptions are now consistently in English.
- **Advanced tab fix** — OTA controls are now guarded correctly so the Advanced tab loads cleanly without update-panel JS errors.
- **Documentation refresh** — guides and architecture notes now describe the current YouTube Live flow, Stream-mode behavior, and the stable `libx264` software encode path.
- **Updated flow diagram** — setup/operation flow image refreshed to match the current system and YouTube Live documentation.

### Validation

- Verified targeted YouTube unit and integration tests pass.
- Verified Web GUI and camera services restart cleanly after deployment.
- Verified Web GUI loads with English labels and updated settings sections on Raspberry Pi hardware.

## v1.2.0

YouTube Live release — performance metrics, async publishing, and Pi 3B+ optimizations.

### Highlights

- **YouTube performance metrics** — publish FPS, average/max publish time, frame counts, and drop rate are now exposed in the runtime status and Web GUI.
- **Async publishing pipeline** — the main capture path now queues frames and never blocks on FFmpeg stdin writes.
- **Lower-latency streaming defaults** — default bitrate reduced to 1500k and FFmpeg preset tuned for speed.
- **Configurable YouTube FPS** — publish FPS can now be selected from 5/10/15/20 in the Web GUI.
- **Throttling removed** — YouTube publishing no longer slows down when local viewers are connected.
- **OTA status hardening** — stale update checks no longer leave the Web GUI stuck in "checking".

### Validation

- Verified on Raspberry Pi 3B+ hardware.
- Confirmed YouTube publishing remains near the configured FPS with no frame skipping under normal load.
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
- All settings are editable in the Web GUI under **Camera → Advanced**.
- `ffmpeg` system package already installed by `install-all-optimized.py`; no extra install step required.
- No changes to OTA, provisioning, or local streaming behaviour.

### Configuration

1. Set up a live event in YouTube Studio and copy the **RTMPS ingest URL** and **Stream key**.
2. In the Web GUI → Settings → Camera (Advanced):
   - Enable **YouTube Live Streaming**.
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

## v1.1.1

Release date: 2026-07-xx

### Highlights

- Incremental maintenance and stability improvements.

## v1.1.0

Release date: 2026-07-xx

### Highlights

- Initial 1.1-series baseline for OTA and service orchestration.

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
