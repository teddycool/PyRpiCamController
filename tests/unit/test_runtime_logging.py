import json
import logging
import queue
import threading
import time
from pathlib import Path

import pytest
import requests
from CamController.LoggingSecure import LoggingSecureHandler, load_logging_key

KEY = "log_" + "a" * 64


class Response:
    def __init__(self, status=200, accepted=1):
        self.status_code = status
        self.headers = {}
        self.accepted = accepted

    def json(self):
        return {"accepted": self.accepted}

    def close(self):
        pass


class Session:
    def __init__(self, outcomes=None):
        self.calls = []
        self.outcomes = list(outcomes or [Response()])
        self.called = threading.Event()

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        self.called.set()
        outcome = self.outcomes.pop(0) if self.outcomes else Response()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self):
        pass


def handler(session, **kwargs):
    return LoggingSecureHandler(
        "example.invalid",
        "/api/device/logs",
        KEY,
        batch_size=1,
        flush_interval=0.01,
        retry_base=0.001,
        session_factory=lambda: session,
        **kwargs,
    )


def record(message="Hello"):
    return logging.LogRecord("cam.test", logging.INFO, __file__, 1, message, (), None)


def wait_done(h):
    deadline = time.monotonic() + 2
    while h._queue.unfinished_tasks and time.monotonic() < deadline:
        time.sleep(0.005)
    assert h._queue.unfinished_tasks == 0


def test_quotes_unicode_traceback_and_redaction():
    session = Session()
    h = handler(session, secrets=("ota-private",))
    try:
        try:
            raise ValueError('password="hidden value"')
        except ValueError:
            import sys

            r = record('Pär "quoted"\nline ' + KEY + " ota-private")
            r.exc_info = sys.exc_info()
        h.emit(r)
        wait_done(h)
        payload = json.loads(session.calls[0][1]["data"])["records"][0]
        assert 'Pär "quoted"\nline' in payload["message"]
        assert KEY not in payload["message"] and "ota-private" not in payload["message"]
        assert "ValueError" in payload["exception"] and "hidden value" not in payload["exception"]
        assert payload["occurred_at"].endswith("Z")
        assert session.calls[0][1]["timeout"] == (3, 5)
        assert session.calls[0][1]["allow_redirects"] is False
    finally:
        h.close()


def test_lost_acknowledgement_retries_same_event():
    session = Session([requests.Timeout(), Response()])
    h = handler(session)
    try:
        h.emit(record())
        wait_done(h)
        assert len(session.calls) == 2
        assert session.calls[0][1]["data"] == session.calls[1][1]["data"]
    finally:
        h.close()


@pytest.mark.parametrize("status", [400, 401, 403, 302])
def test_permanent_errors_do_not_retry(status):
    session = Session([Response(status)])
    h = handler(session)
    try:
        h.emit(record())
        wait_done(h)
        assert len(session.calls) == 1 and h.dropped_records == 1
        if status in (401, 403):
            assert h._disabled.is_set()
    finally:
        h.close()


def test_oversized_control_character_batches_split():
    session = Session()
    h = handler(session)
    try:
        item = {"event_id": "x", "message": "\0" * 8192, "exception": "\0" * 16384}
        h._send(session, [item] * 3)
        assert len(session.calls) >= 2
        assert all(len(call[1]["data"]) <= 262144 for call in session.calls)
    finally:
        h.close()


def test_emit_does_not_wait_for_network_and_queue_is_bounded():
    gate = threading.Event()

    class Slow(Session):
        def post(self, url, **kwargs):
            self.called.set()
            gate.wait(2)
            return Response()

    session = Slow()
    h = handler(session, queue_size=1)
    try:
        h.emit(record())
        assert session.called.wait(1)
        started = time.monotonic()
        for _ in range(20):
            h.emit(record())
        assert time.monotonic() - started < 0.2
        assert h._queue.qsize() <= 1 and h.dropped_records > 0
    finally:
        gate.set()
        h.close()


def test_credential_file_permissions_symlinks_and_format(tmp_path):
    path = tmp_path / "logging.key"
    path.write_text(KEY + "\n")
    path.chmod(0o600)
    assert load_logging_key(path) == KEY
    path.chmod(0o644)
    with pytest.raises(ValueError):
        load_logging_key(path)
    path.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        load_logging_key(link)
    path.write_text("ota-key")
    with pytest.raises(ValueError):
        load_logging_key(path)


def test_no_insecure_transport_or_ota_key():
    with pytest.raises(ValueError):
        LoggingSecureHandler("host", "/logs", KEY, secure=False)
    with pytest.raises(ValueError):
        LoggingSecureHandler("host", "/logs", "a" * 64)


def test_schema_and_main_use_protected_file():
    root = Path(__file__).parents[2]
    schema = json.loads((root / "Settings/settings_schema.json").read_text())["settings"]
    assert schema["LogCredentialFile"]["value"] == "/etc/pycam/logging.key"
    main = (root / "CamController/Main.py").read_text()
    assert "HTTPHandler(" not in main
    assert "load_logging_key" in main
