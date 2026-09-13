# Release Package Specification

## Scope

This document defines the package contract for PyRpiCamController release artifacts.
It is intentionally implementation-neutral and is designed to be consumed by both
PyRpiCamController and PyRpiCamReleaseLab.

## Artifact types

Two artifact types are defined:

1. **Full package** (fresh installation)
   - Purpose: install on a fresh Raspberry Pi.
   - Contains runtime code plus Pi-local installer and selected local probes.

2. **OTA package** (upgrade package)
   - Purpose: upgrade an already-installed device via OTA.
   - Contains runtime and service-update payload needed by device-side OTA flow.

## Package content model (from current repository dependencies)

### Full package must include

- Runtime application and web/UI components:
  - `CamController/`
  - `WebGui/`
  - `Settings/`
  - `Updates/`
  - `Services/`
- Pi-local installation and validation files:
  - `tools/install-all-optimized.py`
  - `tools/validate_installation.sh`
  - Reusable local probes intended to run on device when needed:
    - `tools/test_camera_service.py`
    - `tools/test_web_service.py`
    - `tools/test_smb_service.py`
- Package/runtime metadata:
  - `VERSION`
  - `requirements-pi.txt`
  - `requirements.txt`
  - `LICENSE`
  - `README.md`

### OTA package must include

- Runtime update payload expected by device-side OTA manager:
  - `CamController/`
  - `WebGui/`
  - `Settings/`
  - `Updates/`
  - `Services/`
  - `VERSION`
  - `requirements-pi.txt`

Rationale from current code:
- `Updates/camcontroller_update_manager.py` validates for `CamController/Main.py`, `Settings/settings_manager.py`, `WebGui/web_app.py`, and `VERSION`.
- OTA manager also synchronizes service units from payload `Services/` into `/etc/systemd/system`.

## Files/directories that must never be included in release artifacts

- VCS and CI/dev-only metadata:
  - `.git/`
  - `.github/`
  - `.dev-guidelines/`
- Non-product and non-device payloads:
  - `tests/`
  - `backend/`
  - `build-scripts/`
  - `dist/`
  - `releases/`
  - `.tmp/`
- Python environment/bootstrap/caches and compiled artifacts:
  - virtual/bootstrap environments (`.venv/`, `venv/`, similar)
  - `__pycache__/`
  - `*.pyc`, `*.pyo`
  - tooling caches (`.pytest_cache/`, `.mypy_cache/`, etc.)
- Logs and runtime state:
  - log files and log directories
  - user settings (`Settings/user_settings.json`)
- Credentials/secrets/sensitive machine-local config:
  - credential files, secret templates with real values, environment secret files
  - lab target configuration and deployment report outputs

## Required embedded manifest

Each package must contain generated `RELEASE_MANIFEST.json` at package root with at least:

- `schema_version`
- `product`
- `product_version`
- `candidate_id` (release-candidate identifier)
- `artifact_type` (`full` or `ota`)
- `source_repository`
- `source_commit`
- `builder`
- `build_id`
- `build_timestamp`
- `supported_architecture`
- `supported_pi_models`
- `os_family`
- `ota_min_source_version`
- `reboot_required`

## Required checksum sidecar

- Each artifact must have external SHA-256 sidecar file:
  - `<artifact_filename>.sha256`
- Sidecar format must be compatible with standard `sha256sum -c` workflows.

## Immutability and promotion rules

- **Build once, test once, promote the same bytes**.
- A stable OTA release must be the exact artifact bytes validated by PyRpiCamReleaseLab.
- Approved artifacts must not be rebuilt after approval.

## Identifier separation requirements

The following values are distinct and must not be conflated:

- Product version (`product_version`)
- Release-candidate identifier (`candidate_id`)
- Build identifier (`build_id`)
- Source commit (`source_commit`)
- Artifact checksum (SHA-256)

## Current packaging conflict (documented for future work)

There is an unresolved conflict between existing build paths:

1. `build-scripts/release_manager.py`
   - Uses explicit include lists.
   - Produces both full and OTA package variants.
2. `.github/workflows/create-release.yml`
   - Uses `git archive` over repository state.
   - Produces a different repository-wide tarball.

This task does **not** resolve that conflict; alignment is future work.

## Findings captured (no cleanup in this task)

- Root `VERSION` and `build-scripts/VERSION` differ and require version-authority decision.
- Deployment/smoke scripts contain hardcoded target defaults and environment assumptions.
- `tools/provision_fresh_pi.py` has direct coupling to GitHub Releases URL/tag conventions.
- Credential-like and security-sensitive files exist and need separate security review.
- Historical/temporary tooling artifacts and developer-absolute paths exist in current repository.