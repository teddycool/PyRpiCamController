# Repository Inventory (concise)

This file documents the current tracked top-level files and directories with evidence-based classification, ownership guidance, and a short decision for cleanup or retention. It is intended to reflect the repository state after the OTA server migration (server-side OTA removed to `PyRpiCamOtaBackend`).

- **`CamController/`**: product runtime (camera loop, states, publishers)
  - Evidence: `CamController/Main.py`, unit tests exercise runtime behavior (`tests/unit/*`), referenced by `release-package.yaml`.
  - Owner: PyRpiCamController
  - Decision: keep

- **`WebGui/`**: product web UI (Flask + templates)
  - Evidence: `WebGui/` contains templates and is started by `camcontroller-web.service`; README and INSTALLATION.md reference it.
  - Owner: PyRpiCamController
  - Decision: keep

- **`Settings/`**: settings schema and manager
  - Evidence: `Settings/settings_schema.json` is the golden config; `Settings/settings_manager.py` is imported by runtime and tests.
  - Owner: PyRpiCamController
  - Decision: keep

- **`Services/`**: systemd service files and helper scripts
  - Evidence: `Services/camcontroller.service`, `camcontroller-update.service` used by installer and docs; `tools/install-all-optimized.py` references them.
  - Owner: PyRpiCamController
  - Decision: keep

- **`Updates/`**: device-side OTA manager, daemon, recovery, and tests
  - Evidence: `Updates/camcontroller_update_manager.py`, `Updates/camcontroller_update_daemon.py`, `Updates/recovery.sh`, `Updates/test_updates.py`; unit tests import and exercise related code; `release-package.yaml` includes `Updates/**` in artifacts.
  - Owner: PyRpiCamController
  - Decision: keep (device-side OTA)

- **`backend/Updates/`**: legacy server-side OTA backend (PHP admin, API, DB schema)
  - Evidence: previously present `backend/Updates/api/*.php`, `backend/Updates/admin/*`, `backend/Updates/database/ota_schema.sql`; server-side code has been removed from this repository and is maintained in `PyRpiCamOtaBackend` (private). `docs/OTA_BACKEND_MIGRATION.md` records the migration.
  - Owner: PyRpiCamOtaBackend (private)
  - Decision: removed here; document and link to private backend owner (transitional: documented)

- **`backend/ImagePublisher/`**: image ingestion / publisher backend surface
  - Evidence: present under `backend/`, not migrated; listed in `release-package.yaml` notes as requiring separate review.
  - Owner: unresolved (requires separate review)
  - Decision: retain for separate ownership review

- **`tools/`**: installer, provisioning, test probes, and mock servers
  - Evidence: contains `install-all-optimized.py`, `provision_fresh_pi.py`, `mock_ota_server.py`, `secure_enroll_device.py`, and test probes referenced by release manifest and tests.
  - Owner: PyRpiCamController (provisioning and probes) / PyRpiCamReleaseLab (remote orchestration scripts are transitional)
  - Decision: keep; classify remote orchestration scripts (`provision_fresh_pi.py`, `smoke_test_pi.sh`, `deploy_and_test.sh`) as transitional to ReleaseLab (documented)

- **`build-scripts/`** and `.github/workflows/create-release.yml`**: release packaging and CI workflows
  - Evidence: `build-scripts/release_manager.py` (explicit include list) and `.github/workflows/create-release.yml` (git-archive based) both exist; `release-package.yaml` documents artifact contract.
  - Owner: PyRpiCamController (packaging definitions); ReleaseLab will consume artifacts
  - Decision: keep both paths operational and mark alignment as unresolved—documented in `RELEASE_PACKAGE_SPEC.md` and `release-package.yaml`.

- **`tests/`**: unit and integration tests
  - Evidence: `tests/unit` and `tests/integration` run via `tests/run_tests.py`; unit tests pass (77/77) in local verification.
  - Owner: PyRpiCamController
  - Decision: keep

- **`.dev-guidelines/`** and top-level guidance files (`CONTRIBUTING.md`, `SYSTEM_PROMPT.md`, `AI_INSTRUCTIONS.md`)**
  - Evidence: developer-facing rules; mandatory for AI assistants and contributors per `CONTRIBUTING.md`.
  - Owner: PyRpiCamController (developer docs)
  - Decision: keep; remove duplicate documents only when clearly obsolete (one duplicate `HARDWARE_METADATA_STRATEGY.md` removed from `.dev-guidelines/` during this task)

- **Credential & config templates**: `tools/ota_credentials.txt`, `tools/ota_config.json`, `backend/ImagePublisher/utils/secrets_tmpl.php`, `tools/ota_credentials.txt.template` etc.
  - Evidence: tracked files appear to be templates or placeholders (`SET_IN_LOCAL_UNTRACKED_COPY`, instructions in `secrets_tmpl.php`). `release-package.yaml` explicitly excludes credential files from artifacts.
  - Owner: PyRpiCamController (templates); runtime secret owners must maintain untracked local copies
  - Decision: retain templates but flag for security review if any tracked file contains real credentials (none found during this audit)

- **Obsolete / developer-only candidates removed (staged and not committed in earlier work or removed now)**
  - `debug_packaging.py` — removed (tracked dev helper)
  - `build-scripts/test_package.py` — removed (dev packaging helper)
  - `tools/timelaps.py` — removed (developer-local timelapse helper)
  - `test_upload.php` — removed (legacy backend utility)
  - `version_management_new.php` — removed (legacy utility)
  - Evidence: These were either referenced only in developer notes or had hardcoded absolute paths and were listed in `release-package.yaml` as obsolete candidates.

## Version Source Decision (evidence + recommendation)

- Observed divergence:
  - `VERSION` (root): `1.8.3`
  - `build-scripts/VERSION`: `1.2.1`
  - `pyproject.toml` project.version: `1.0.0`

- Recommendation (non-invasive): treat root `VERSION` as the canonical product version for now. Document divergence in `RELEASE_PACKAGE_SPEC.md` and do not change any packaging code in this cleanup task. A follow-up change should unify callers to read root `VERSION`.

## Notes & Next Steps

- Run `git status --short` to review staged deletions before committing; this task staged several deletions but did not commit (by request).
- Security: rotate secrets if any tracked file is found to contain real credentials; currently the tracked files are templates/placeholders.
- Release workflow: leave both `build-scripts/release_manager.py` and `.github/workflows/create-release.yml` operational; record alignment as an unresolved decision for ReleaseLab owners.
