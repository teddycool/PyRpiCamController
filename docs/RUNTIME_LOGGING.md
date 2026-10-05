# Secure runtime logging

The camera service sends structured log batches to PyRpiCamOtaBackend over HTTPS.
It uses a **separate logging key per device**. OTA keys never authenticate log
uploads. The backend's `RUNTIME_LOGGING_API.md` defines payloads and limits.

## Deployment prerequisites

Deploy and rehearse the backend migration first. Updated enrollment requires the
backend to return `logging_api_key` alongside the OTA credential. No new Pi
package or service is required (`requests` is already a runtime dependency).
The installer creates `/etc/pycam`; provisioning creates the credential file.
The camera service currently runs as root, so this file is root-owned, mode 0600:

```
/etc/pycam/logging.key
```

It is outside the repository and SMB share, survives OTA updates, and is not
included in settings exports, diagnostic collection or release packages. If the
camera service account changes, make the file privately readable by that account.
Symlinks, nonregular files and group/world-readable credentials are rejected.

## Existing devices

In the backend admin page, open Runtime Logs, select the registered device and
create a logging key. Run this from your development computer in the updated
CamController checkout (substitute the SSH host/user and backend URL):

```bash
python3 tools/provision_logging_key.py \
  --host <pi-host> --ssh-user <user> \
  --backend-url https://www.sensorwebben.se/pycamota
```

Paste the key into the hidden prompt. It travels through SSH stdin rather than
process arguments. The tool writes it atomically using sudo, configures logging
and restarts `camcontroller.service`. SSH must permit noninteractive sudo; changed
known host keys are rejected. Initial unknown hosts use SSH accept-new behaviour.
For rotation, create a replacement in the admin page and run the tool within the
ten-minute overlap. Keep the old device configuration until the replacement is
available. Revocation affects logging only, without modifying the OTA credential.

## New devices

Enrollment always provisions both keys. Remote uploads remain off by default.
To explicitly enable logging as part of enrollment:

```bash
python3 tools/secure_enroll_device.py --host <pi-host> --ssh-user <user> \
  --enable-logging
```

The full provisioning tool also accepts `--enable-logging`, passing it through to
enrollment. Enabling logging restarts the camera service. Use the updated
provisioning scripts from your development checkout, not an older release's copy.

## Settings and behaviour

| Setting | Purpose/default |
|---|---|
| LogToServer | Off by default; enable after key provisioning |
| LogHost | Backend hostname, including optional port; no scheme |
| LogUrl | `/pycamota/api/device/logs`; adjust to deployed base path |
| LogCredentialFile | `/etc/pycam/logging.key`; contains the logging-only key |
| LogServerLevel | `info`; independent of local LogLevel |
| LogQueueSize | 1000 buffered records, maximum 10000 |
| LogBatchSize | 10; permitted range 1–10 |

There is no inline LogApiKey setting. Existing inline keys and legacy plaintext
GET uploads are no longer used. Missing credentials disable remote logging with
an error, while local logging continues. Only the `cam` logger hierarchy in the
camera service is uploaded; WebGui/update-daemon/metrics logs are not automatically
forwarded by this change.

The worker batches for up to two seconds, sends with 3-second connect and 5-second
read timeouts, verifies TLS certificates and rejects redirects. Transient failures
retry the same event UUIDs up to five times after the first attempt. Server-side
unique event IDs avoid duplicates after lost acknowledgements. Permanent payload
errors are dropped; rejected credentials disable uploads until service restart.

The queue is memory-only. Outages can overflow it, and shutdown/reboot loses
pending records. Local logs remain the source for complete on-device diagnostics;
this feature is best-effort centralized logging, not a durable audit ledger.
Dropped-record counts are reported to stderr without secret-bearing payloads.

## Troubleshooting and checks

Check the camera journal for `Remote logging:` diagnostics. For rejected credentials,
rotate/provision the key and restart. For no uploads, check LogToServer, hostname,
base path, TLS/clock correctness and the private credential file permissions.
Do not print the credential or include it in a support bundle.

```bash
python3 -m pytest tests/ -v
```

Tests cover Unicode/multiline exceptions, redaction, finite retries, nonblocking
logging, queue overflow, rejected credentials and protected-file validation.
Backend tests cover migration, ingest, key lifecycle, filtering, safe rendering
and retention. The old ImagePublisher `Camlog` table/endpoints are separate legacy
plumbing and are not used or automatically migrated by this implementation.

## Implementation validation

The complete repository suite passed (102 tests). The new uploader had 85% line
coverage. Backend migration/API/OTA tests passed against MariaDB 10.11 and PHP 8.3
in scratch databases. Actual Docker/Apache behaviour, production HTTPS and a
physical Pi smoke test remain deployment checks; see the backend rollout guide.
