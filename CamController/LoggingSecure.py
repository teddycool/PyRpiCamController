"""Bounded asynchronous runtime logging. Never sends OTA credentials."""

import datetime as dt
import json
import logging
import os
import queue
import re
import stat
import sys
import threading
import time
import uuid
from urllib.parse import urlsplit

import requests

KEY_RE = re.compile(r"log_[a-f0-9]{64}\Z")


def load_logging_key(path: str) -> str:
    """Read a private regular file without following symlinks."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_mode & 0o077
            or info.st_uid not in {0, os.geteuid()}
            or info.st_size > 256
        ):
            raise ValueError(
                "Logging credential file must be private and owned by the service user or root"
            )
        with os.fdopen(fd, "r", encoding="ascii", closefd=False) as stream:
            key = stream.read(256).strip()
        if not KEY_RE.fullmatch(key):
            raise ValueError("Invalid logging credential")
        return key
    finally:
        os.close(fd)


def redact_text(value: object, secrets=()) -> str:
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"\blog_[a-f0-9]{64}\b|\b[a-f0-9]{64}\b", "[REDACTED]", text, flags=re.I)
    text = re.sub(r"\bBearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", text, flags=re.I)
    return re.sub(
        r"((?:api[_-]?key|password|passwd|token|secret|authorization)[\"']?\s*[:=]\s*)(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;&]+)",
        r"\1[REDACTED]",
        text,
        flags=re.I,
    )


def bounded_text(value, size, secrets=()):
    return (
        redact_text(value, secrets)
        .encode("utf-8", errors="replace")[:size]
        .decode("utf-8", errors="ignore")
    )


class LoggingSecureHandler(logging.Handler):
    def __init__(
        self,
        host,
        url,
        api_key,
        secure=True,
        *,
        level=logging.INFO,
        queue_size=1000,
        batch_size=10,
        flush_interval=2.0,
        app_version=None,
        secrets=(),
        session_factory=requests.Session,
        max_retries=5,
        retry_base=1.0,
    ):
        super().__init__(level)
        endpoint = f"https://{host}{url}"
        parsed = urlsplit(endpoint)
        if (
            not secure
            or not KEY_RE.fullmatch(api_key)
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not url.startswith("/")
            or "://" in host
        ):
            raise ValueError("HTTPS endpoint and dedicated logging key required")
        if not 1 <= batch_size <= 10 or not 1 <= queue_size <= 10000 or flush_interval <= 0:
            raise ValueError("Invalid logging queue configuration")
        self.endpoint = endpoint
        self._key = api_key
        self._secrets = tuple(secrets) + (api_key,)
        self.app_version = app_version
        self.session_id = str(uuid.uuid4())
        self._queue = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self._disabled = threading.Event()
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._session_factory = session_factory
        self._max_retries = max_retries
        self._retry_base = retry_base
        self.dropped_records = 0
        self._last_notice = 0.0
        self._worker = threading.Thread(target=self._run, name="runtime-log-upload", daemon=True)
        self._worker.start()

    def _drop(self, count, reason):
        self.dropped_records += count
        now = time.monotonic()
        if now - self._last_notice >= 60:
            # Bypass logging to prevent recursion; never echo payload or credentials.
            print(
                f"Remote logging: {reason}; dropped total={self.dropped_records}", file=sys.stderr
            )
            self._last_notice = now

    def emit(self, record: logging.LogRecord) -> None:
        if self._stop.is_set() or self._disabled.is_set():
            self._drop(1, "upload disabled")
            return
        try:
            exception = (
                logging.Formatter().formatException(record.exc_info) if record.exc_info else None
            )
            item = {
                "event_id": str(uuid.uuid4()),
                "occurred_at": dt.datetime.fromtimestamp(record.created, dt.timezone.utc)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
                "level": (
                    record.levelname
                    if record.levelname in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
                    else "INFO"
                ),
                "logger": bounded_text(record.name, 128, self._secrets),
                "message": bounded_text(record.getMessage(), 8192, self._secrets)
                or "(empty message)",
                "exception": bounded_text(exception, 16384, self._secrets) if exception else None,
                "app_version": (
                    bounded_text(self.app_version, 32, self._secrets) if self.app_version else None
                ),
                "session_id": self.session_id,
            }
            self._queue.put_nowait(item)
        except queue.Full:
            self._drop(1, "queue full")
        except Exception:
            self._drop(1, "record serialization failed")

    def _send(self, session, batch):
        # ensure_ascii=False keeps ten maximum-sized records below the body cap.
        payload = json.dumps({"records": batch}, ensure_ascii=False).encode("utf-8")
        # Escaped control characters can expand significantly. Reject rather than
        # repeatedly sending a batch the server can never accept.
        if len(payload) > 262144:
            if len(batch) > 1:
                middle = len(batch) // 2
                self._send(session, batch[:middle])
                self._send(session, batch[middle:])
            else:
                self._drop(1, "record exceeds batch byte limit")
            return
        for attempt in range(self._max_retries + 1):
            if self._stop.is_set() or self._disabled.is_set():
                self._drop(len(batch), "upload stopped")
                return
            delay = min(60, self._retry_base * 2**attempt)
            try:
                response = session.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self._key}",
                        "Content-Type": "application/json",
                    },
                    data=payload,
                    timeout=(3, 5),
                    allow_redirects=False,
                )
                try:
                    if response.status_code == 200:
                        try:
                            if response.json().get("accepted") == len(batch):
                                return
                        except (ValueError, AttributeError):
                            pass  # Bad/lost acknowledgement: retry same event UUIDs.
                    elif response.status_code in (401, 403):
                        self._disabled.set()
                        self._drop(len(batch), "credentials rejected; restart after provisioning")
                        return
                    elif response.status_code != 429 and response.status_code < 500:
                        self._drop(len(batch), "batch rejected")
                        return
                    if response.status_code == 429:
                        try:
                            delay = min(
                                60, max(delay, float(response.headers.get("Retry-After", "60")))
                            )
                        except ValueError:
                            delay = 60
                finally:
                    response.close()
            except requests.RequestException:
                pass
            if attempt < self._max_retries and self._stop.wait(delay):
                break
        self._drop(len(batch), "retry budget exhausted")

    def _run(self):
        session = self._session_factory()
        # No automatic retry adapter: retry ownership stays here.
        try:
            while not self._stop.is_set():
                try:
                    first = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                batch = [first]
                deadline = time.monotonic() + self._flush_interval
                while len(batch) < self._batch_size and not self._stop.is_set():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        batch.append(self._queue.get(timeout=min(0.1, remaining)))
                    except queue.Empty:
                        continue
                try:
                    self._send(session, batch)
                finally:
                    for _ in batch:
                        self._queue.task_done()
        finally:
            session.close()
            while True:
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                    self._drop(1, "upload stopped")
                except queue.Empty:
                    break

    def close(self) -> None:
        self._stop.set()
        if threading.current_thread() is not self._worker:
            self._worker.join(timeout=9)
        super().close()
