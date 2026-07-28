# Security Baseline v1 (Production Cameras)

This document defines a practical minimum security baseline for large-scale PyRpiCamController deployments.

Scope: hundreds of internet-connected devices, OTA for application/services, no always-on remote shell operations.

## Goals

- Keep fleet operations simple and predictable
- Minimize blast radius if one device is compromised
- Avoid secret sprawl (no plaintext passwords in backend)
- Preserve supportability through logs + controlled maintenance paths

## Baseline Controls

### 1) Identity and Credentials

- Each device has a unique device identity (`device_id` / CPU serial)
- Each device has a unique OTA API key
- Shared/default SSH passwords are forbidden
- SSH private keys are never stored in backend or repository
- Backend stores metadata only (fingerprints/status), never plaintext secrets

### 2) SSH Posture

- Default production posture: SSH disabled or key-only
- Password SSH login should be disabled after provisioning
- If SSH is enabled, use unique keys per operator or per environment
- No internet-exposed password SSH access

### 3) OTA Scope and Trust Boundary

- OTA is used for project-controlled application/services/config updates
- OTA does not perform unrestricted OS upgrades by default
- OTA update integrity must be verified before apply
- Rollback/backup behavior must stay enabled for failed updates

### 4) Linux Security Updates

- Enable unattended **security** updates (not broad distro upgrades)
- Reboot policy for kernel/security updates must be explicit
- Test updates on canary devices first before broad rollout
- Major distro upgrades are planned maintenance events, not ad-hoc OTA actions

### 5) Network Exposure

- Avoid direct inbound management ports from the public internet
- Only required service ports should be open
- Device-initiated outbound connectivity is preferred for backend communication

### 6) Logging and Auditability

- Device logs remain available locally to customer/support (`shared/logs`)
- Support troubleshooting workflow is log-first
- Backend tracks deployment/upgrade events and health timestamps
- Access/security-relevant actions should be timestamped and attributable

### 7) Data Handling

- No plaintext credentials in logs
- No secrets in stickers, screenshots, or exported reports
- Device labels/stickers should include non-secret identifiers only
  - device name
  - serial/device ID
  - support URL/QR

## Fleet Metadata (Recommended DB Fields)

Store only state metadata needed for operations:

- `device_id`
- `device_name`
- `location`
- `channel` / `update_group`
- `last_seen_at`
- `current_version`
- `provisioned_at`
- `ssh_enabled` (boolean)
- `ssh_auth_mode` (`disabled` / `key_only`)
- `ssh_key_fingerprint` (optional)
- `password_changed_at` (timestamp, optional; never store password)

## Provisioning Checklist (v1)

- [ ] Deploy from signed/controlled release or local trusted build
- [ ] Enroll device and obtain unique OTA API key
- [ ] Verify OTA settings (`OtaEnable`, `OTA.server_url`, `OTA.api_key`)
- [ ] Ensure required services are active
- [ ] Rotate/disable default SSH password
- [ ] Set SSH to key-only or disable SSH for production
- [ ] Confirm logs are writable and retrievable
- [ ] Record non-secret metadata in backend

## Release Gate Checklist (v1)

Before rollout to production group:

- [ ] Canary test passed on target Pi models
- [ ] Upgrade + rollback path validated
- [ ] Security updates policy confirmed (security-only)
- [ ] No credential leaks in release artifacts/docs
- [ ] Provisioning script validates service health and OTA config

## Incident Response (v1)

If a device is suspected compromised:

1. Remove device from production update group
2. Revoke/rotate OTA API key
3. Disable SSH access (or rotate authorized keys)
4. Collect logs and backend audit data
5. Re-provision from trusted image/release if needed

## Out of Scope for v1

- Full remote support-session broker
- Per-session ephemeral access certificates
- Zero-trust remote shell workflows

These can be introduced in a later phase when operational needs justify added complexity.
