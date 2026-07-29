# Release Notes

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
