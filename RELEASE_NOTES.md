# Release Notes

This file is the canonical project changelog.

- Newest release is always at the top.
- Historical entries are kept below.
- Per-build notes are also generated in `dist/release-notes-<version>.md`.

## v1.8.2

Release date: 2026-09-02

### Highlights

- [Add release highlights]

### Validation

- [Add validation notes]

## v1.8.2

Release date: 2026-09-02


### Highlights

- YouTube FFmpeg streaming configuration modernized and hardened:
  - Replaced deprecated FFmpeg `-vsync cfr` with `-fps_mode cfr` for modern FFmpeg compatibility.
  - Fixed color range handling on MJPEG input by moving `-color_range tv` before input format specification, eliminating recurring swscaler warnings about deprecated pixel formats.
  - Increased H.264 level from 4.0 to 5.1 to properly support 2304×1296 resolution (Pi5 camera) and higher frame configurations across all Raspberry Pi generations.
  - These changes eliminate ~30+ FFmpeg warnings per initialization while maintaining stream stability and compatibility.

### End-user summary

- YouTube Live streaming now initializes cleanly without FFmpeg format warnings.
- Better support for high-resolution streams on Pi5 with proper H.264 level constraints.
- Stream quality and latency behavior remain unchanged—this is a configuration/compatibility fix.

### Validation

- Confirmed YouTube publisher initializes without deprecation or swscaler warnings in service logs.
- Verified on Raspberry Pi 5 with 2304×1296 resolution at 15 fps (YouTube ingest).
- H.264 level 5.1 is YouTube-standard and backwards-compatible with all Pi3/Pi4/Pi5 hardware.

## v1.7.1

Release date: 2026-08-30


### Highlights

- Stream pipeline now includes local recording alongside local MJPEG streaming and YouTube Live forwarding:
  - Added a recorder branch that forwards the shared encoded MJPEG stream into segmented local files.
  - Added recorder-aware runtime flow so recording can run in parallel with the existing stream and YouTube paths.
  - Kept the local viewer branch and YouTube ingest path intact while making the recording branch first-class in the runtime architecture.
- Settings schema and Web GUI layout mapping improvements:
  - Clarified how nested schema keys are flattened into web-editable fields for the GUI.
  - Added explicit routing rules so `Cam.publishers.youtube.*` fields render under **YouTube Live** even when their schema metadata still says `Camera`.
  - Kept field labels driven by `ui.name` while section headers are driven by GUI grouping rules.
- OTA release packaging was reduced:
  - Added a lean OTA tarball that contains only the runtime code needed on the device.
  - Preserved the full release tarball for fresh provisioning and installer workflows.
  - Reduced download size for OTA updates without changing the update flow on the Pi.
- Metrics and observability continue to cover the stream runtime:
  - Structured metrics logs still capture temperature, CPU load, storage, mode, and stream state changes.
  - Historical graph markers continue to show mode and YouTube transitions directly in the Web GUI.
- Web GUI local stream status now shows recording state:
  - Added a Recording active/inactive indicator to the Local Stream status panel.
  - The status now comes from the runtime stream payload, alongside the existing YouTube Live status.

### End-user summary

- You can now record the local stream while still streaming normally and forwarding to YouTube.
- The Settings page is easier to understand because related YouTube options appear together in their own section.
- OTA updates should download faster because the update package is smaller.
- Metrics and status history remain available in the Web GUI to help with troubleshooting and performance checks.
- The Local Stream panel now shows whether local recording is active or inactive.

### Validation

- Verified the Settings schema to Web GUI mapping so `Cam.publishers.youtube.*` fields render under **YouTube Live** while keeping `ui.name` as the field label.
- Synced the updated `settings_schema.json` to the Raspberry Pi 5 target (`192.168.1.89`) and confirmed `camcontroller.service` and `camcontroller-web.service` restarted successfully.
- Confirmed the release packager now emits both a full tarball for provisioning and a lean `-ota.tar.gz` package for OTA delivery.
- Reviewed the new recording branch and release notes updates alongside the stream pipeline and metrics work already validated on target hardware.

## v1.6.1

Release date: 2026-08-29


### Highlights

- Raspberry Pi 5 dual-camera interface support end-to-end:
  - Added configurable camera interface index (`CamInterface`) in hardware config template/runtime config.
  - Added shared Picamera2 interface selection helper and wired it into `PiCam2`, `PiCam3`, and `PiCamHQ` camera backends.
  - Added installer/provisioner support to set and propagate camera interface selection during deployment.
- Provisioning and installation hardening:
  - Added apt/dpkg lock waiting and retry behavior to reduce install failures caused by `unattended-upgrades` contention.
  - Improved production provisioning auth flow for OTA enrollment (including non-interactive/admin-password compatible paths).
- Network/comitup startup behavior hardened for field reliability:
  - Added explicit `comitup` start condition script so AP portal starts only when no real client network is available.
  - Prevented runtime auto-start of `comitup` when network drops after boot.
  - Updated camera/web/update services to wait for real network readiness and avoid AP/normal-mode port contention races.
- Web GUI white-balance calibration improvements:
  - Added guided white-balance calibration action in Advanced settings, above White Balance Mode.
  - Calibration samples AWB metadata from a white-paper reference and stores manual red/blue gains.
  - Auto White Balance is set to off after calibration so calibrated manual values are used.
  - If camera/stream service is running, calibration stops `camcontroller.service` automatically before sampling and starts it again after calibration.
  - Added recovery start attempt if calibration fails after stopping the service.
- YouTube Live stability hardening for long-running streams:
  - Removed FFmpeg `-re` from live stdin pipeline to prevent pacing drift and ingest buffering.
  - Moved FPS control to output side and enforced constant frame rate with `-vsync cfr`.
  - Anchored output timestamps to wall clock with `-use_wallclock_as_timestamps 1` to reduce long-run PTS drift.
  - Added adaptive x264 preset by Pi generation (`ultrafast` on Pi4/older, `fast` on Pi5+) for better hardware-fit stability.
  - Reduced FFmpeg pipe queue pressure and changed frame queue behavior to drain stale backlog frames instead of bursting old frames.
  - Added continuous FFmpeg stderr capture into service logs for live ingest diagnostics.
- End-user documentation updates:
  - Added white-balance calibration guidance to both English and Swedish user manuals.
  - Added note that cameras purchased from sensorwebben.se are already calibrated.

### End-user summary

- Added a one-click white-balance calibration in Advanced settings for faster, more reliable color setup.
- Improved YouTube Live stability during long streams, with fewer buffering events and less quality drop over time.
- Better reliability on Raspberry Pi devices through safer startup/network behavior and installation/provisioning hardening.
- Included updated documentation (English and Swedish) to make setup and daily operation easier.

### Validation

- Verified Pi5 provisioning and runtime on target hardware (`192.168.1.86`) including service restarts and stream startup.
- Confirmed streaming service uses encoded camera-native path and remains active with expected port ownership.
- Validated comitup behavior with live tests:
  - network-present boot: `comitup` skipped via `ExecCondition`;
  - no-network condition: `comitup` can start;
  - runtime network loss: `comitup` stays inactive (no auto-start regression).
- Confirmed branch changes include camera backend/interface updates, provisioning/install scripts, and service-gating scripts/units.
- Verified WB calibration endpoint and Web GUI integration on target devices.
- Synced and restarted services on Raspberry Pi targets (`192.168.1.140` and `192.168.1.89`), services confirmed active after deployment.
- Validated YouTube Live runtime tuning on both Pi targets with service restarts and active stream process verification.
- Verified Pi4 runs YouTube with adaptive `ultrafast` preset and reduced encoder thermals compared to fixed `fast` preset.
- Confirmed updated FFmpeg command line contains wall-clock timestamping and CFR output settings after deployment.

## v1.5.12

Release date: 2026-08-23

### Highlights

- Bugfix release for Web GUI metrics history parsing.
- Fixed metrics graph data loading so it reads both the active metrics log (`cam-metrics.log`) and rotated files (`cam-metrics.log.1`, `.2`, etc.).
- Restored expected 24-hour graph continuity when older samples have already rotated out of the active log file.
- Added retention sizing safeguards for metrics log rotation so configured file size/rotation can reliably preserve ~24 hours of metrics data.

### Validation

- Added and ran unit tests covering rotated metrics log parsing and 24-hour filtering behavior.
- Verified existing metrics Web GUI tests continue to pass.

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
