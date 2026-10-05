"""Regression tests for secure OTA enrollment."""

import base64
import json
import subprocess

from tools import secure_enroll_device


def test_remote_settings_script_uses_privileged_batch_save():
    """Enrollment may set the protected API key without partial settings saves."""
    payload = {
        "api_key": "secret-test-key",
        "server_url": "https://example.invalid/ota",
        "update_group": "production",
        "test_device": False,
        "device_name": "Test camera",
    }
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    script = secure_enroll_device.build_remote_settings_script(encoded)

    assert "'OTA.api_key'," in script
    assert "allow_readonly=True" in script
    assert script.count("save=False") == 6
    assert script.count("settings_manager.save_user_settings()") == 1


def test_command_failure_does_not_print_remote_command(monkeypatch, capsys):
    """A failed SSH command must not echo its credential-bearing payload."""
    secret = "credential-that-must-not-be-logged"
    monkeypatch.setattr(
        secure_enroll_device,
        "parse_args",
        lambda: type(
            "Args",
            (),
            {
                "admin_password": "password",
                "admin_username": "admin",
                "ota_base_url": "https://example.invalid",
                "host": "camera.invalid",
                "ssh_user": "pi",
                "ssh_port": 22,
                "ssh_key": None,
            },
        )(),
    )
    monkeypatch.setattr(
        secure_enroll_device,
        "setup_ssh_session",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(
                returncode=1,
                cmd=["ssh", f"payload={secret}"],
                stderr="remote failure",
            )
        ),
    )
    monkeypatch.setattr(secure_enroll_device, "close_ssh_session", lambda *args: None)

    assert secure_enroll_device.main() == 1
    captured = capsys.readouterr()
    assert secret not in captured.err
    assert "exit code 1" in captured.err



def test_logging_key_sent_over_stdin_not_remote_command(monkeypatch):
    captured = {}
    monkeypatch.setattr(secure_enroll_device, 'run_ssh',
        lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs))
    key = 'log_' + 'a'*64
    secure_enroll_device.push_logging_key_to_pi('pi.invalid', 'pi', 22, key)
    assert key not in captured['args'][3]
    assert captured['kwargs']['input_text'] == key+'\n'
    assert 'os.fchmod(fd,0o600)' in captured['args'][3]
    assert 'os.replace' in captured['args'][3]
    assert 'os.fsync(parent)' in captured['args'][3]


def test_enrollment_requires_separate_logging_key(monkeypatch):
    class Response:
        status_code = 201
        def json(self): return {'device_id':'test','api_key':'ota','logging_api_key':'log_'+'a'*64}
    monkeypatch.setattr(secure_enroll_device.requests, 'post', lambda *a, **k: Response())
    cfg = secure_enroll_device.BackendConfig('https://example.invalid','admin','password')
    result = secure_enroll_device.consume_enrollment_token(cfg,'token','test','Test','')
    assert result.api_key != result.logging_api_key
