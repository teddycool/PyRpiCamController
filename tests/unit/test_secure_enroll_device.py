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
