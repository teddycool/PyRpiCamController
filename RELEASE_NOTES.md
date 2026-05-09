# Release Notes

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
- Support for Raspberry Pi Camera Module 2, Camera Module 3, HQ Camera, and USB webcam fallback.

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
