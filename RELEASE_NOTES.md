# Release Notes

## v1.0.6

OTA is now production-ready and validated on Raspberry Pi hardware.

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

## v1.0.0 (Draft)

First stable baseline release of PyRpiCamController for Raspberry Pi camera deployments.

### Highlights

- Web-based camera configuration with auto-save and apply/restart workflow.
- Dual operating modes:
  - Camera mode for scheduled image capture and file publishing.
  - Stream mode for live video streaming.
- Built-in SMB file sharing for captured images and logs.
- Unified JSON schema settings system.
- Temperature monitoring and system status visibility in the Web UI.
- Support for Raspberry Pi Camera Module 2, Camera Module 3, and HQ Camera.
- Stream mode uses native encoded MJPEG on Raspberry Pi camera modules with client-aware idle framerate throttling.

### Included in this release

- Core camera controller runtime and state handling.
- Web GUI with settings management and status panels.
- Streaming server integration and stream status API.
- SMB and network service files for deployment.
- Installation, troubleshooting, and user documentation updates.

### Production scope

- Supported production scope: camera runtime, web UI, SMB sharing, and WiFi setup.
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
