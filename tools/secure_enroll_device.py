#!/usr/bin/env python3
"""
Secure OTA enrollment tool (run on development/admin computer).

Flow:
1) SSH into target Pi and read CPU serial
2) Admin-auth to OTA backend and create one-time enrollment token
3) Send token + CPU serial to backend enroll endpoint
4) Backend creates/rotates API key and returns it once
5) Write OTA settings on Pi and restart OTA daemon

Security model:
- Admin credentials stay on dev computer only
- Backend stores token hash, not plaintext token
- Token is one-time and short-lived
- Device never receives admin credentials
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


DEFAULT_OTA_BASE = "https://www.sensorwebben.se/pycamota"


@dataclass
class BackendConfig:
    base_url: str
    username: str
    password: str


@dataclass
class DeviceEnrollmentResult:
    device_id: str
    api_key: str
    channel: str


class EnrollmentError(RuntimeError):
    pass


_SSH_CONTROL_PATH: Optional[str] = None
_SSH_IDENTITY_FILE: Optional[str] = None


def run_cmd(cmd: List[str], capture: bool = True, check: bool = True, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=capture,
        check=check,
        input=input_text,
    )


def run_ssh(host: str, ssh_user: str, ssh_port: int, remote_cmd: str, capture: bool = True) -> subprocess.CompletedProcess:
    cmd = [
        "ssh",
        "-o", "ControlMaster=auto",
        "-o", "ControlPersist=600",
        "-o", "SendEnv=none",       # suppress locale forwarding (avoids LC_ALL warnings on Pi)
        "-o", "StrictHostKeyChecking=no",
    ]

    if _SSH_IDENTITY_FILE:
        cmd += ["-i", _SSH_IDENTITY_FILE]

    if _SSH_CONTROL_PATH:
        cmd += [
            "-o",
            f"ControlPath={_SSH_CONTROL_PATH}",
        ]

    cmd += [
        "-p",
        str(ssh_port),
        f"{ssh_user}@{host}",
        remote_cmd,
    ]
    return run_cmd(cmd, capture=capture, check=True)


def setup_ssh_session(host: str, ssh_user: str, ssh_port: int, identity_file: Optional[str] = None) -> None:
    """Initialize SSH ControlMaster so password is asked once and reused for this session."""
    global _SSH_CONTROL_PATH, _SSH_IDENTITY_FILE

    if identity_file:
        _SSH_IDENTITY_FILE = identity_file

    if _SSH_CONTROL_PATH:
        return

    control_dir = tempfile.mkdtemp(prefix="camctl-ssh-")
    _SSH_CONTROL_PATH = os.path.join(control_dir, "cm-%C")

    cmd = [
        "ssh",
        "-o", "ControlMaster=auto",
        "-o", "ControlPersist=600",
        "-o", "SendEnv=none",       # suppress locale forwarding
        "-o", "StrictHostKeyChecking=no",
        "-o", f"ControlPath={_SSH_CONTROL_PATH}",
        "-p", str(ssh_port),
    ]
    if _SSH_IDENTITY_FILE:
        cmd += ["-i", _SSH_IDENTITY_FILE]
    cmd += [f"{ssh_user}@{host}", "true"]
    run_cmd(cmd, capture=True, check=True)


def close_ssh_session(host: str, ssh_user: str, ssh_port: int) -> None:
    """Close SSH ControlMaster session if active."""
    global _SSH_CONTROL_PATH

    if not _SSH_CONTROL_PATH:
        return

    cmd = [
        "ssh",
        "-O",
        "exit",
        "-o",
        f"ControlPath={_SSH_CONTROL_PATH}",
        "-p",
        str(ssh_port),
        f"{ssh_user}@{host}",
    ]

    try:
        run_cmd(cmd, capture=True, check=False)
    finally:
        _SSH_CONTROL_PATH = None


def get_remote_cpu_serial(host: str, ssh_user: str, ssh_port: int) -> str:
    remote = "awk -F': *' '/^Serial/{print tolower($2)}' /proc/cpuinfo | head -n1"
    result = run_ssh(host, ssh_user, ssh_port, remote)
    serial = result.stdout.strip().lower().replace("0x", "")
    if not serial:
        raise EnrollmentError("Could not read CPU serial from remote Pi (/proc/cpuinfo)")
    return serial


def normalize_cpu_id(cpu_id: str) -> str:
    clean = cpu_id.strip().lower().replace("0x", "")
    if not clean:
        raise EnrollmentError("Empty CPU ID")
    if any(ch not in "0123456789abcdef" for ch in clean):
        raise EnrollmentError(f"CPU ID contains non-hex characters: {cpu_id}")
    return clean


def admin_login(session: requests.Session, cfg: BackendConfig) -> None:
    login_url = f"{cfg.base_url}/admin/admin_login.php"
    response = session.post(
        login_url,
        data={"username": cfg.username, "password": cfg.password},
        timeout=30,
        allow_redirects=True,
    )

    # Success path lands on admin dashboard and has no login error message.
    if response.status_code != 200:
        raise EnrollmentError(f"Admin login failed: HTTP {response.status_code}")

    text = response.text.lower()
    if "invalid username or password" in text or "please enter username and password" in text:
        raise EnrollmentError("Admin login failed: invalid credentials")


def create_enrollment_token(
    session: requests.Session,
    cfg: BackendConfig,
    device_id: str,
    name: str,
    channel: str,
    notes: str,
    ttl_minutes: int,
) -> str:
    url = f"{cfg.base_url}/api/enrollment_create.php"
    payload: Dict[str, Any] = {
        "device_id": device_id,
        "device_name": name,
        "channel": channel,
        "notes": notes,
        "ttl_minutes": ttl_minutes,
    }
    response = session.post(url, json=payload, timeout=30)
    if response.status_code != 201:
        raise EnrollmentError(f"Failed to create enrollment token: HTTP {response.status_code} {response.text[:240]}")
    data = response.json()
    token = str(data.get("token", ""))
    if not token:
        raise EnrollmentError("Enrollment token missing in response")
    return token


def consume_enrollment_token(cfg: BackendConfig, token: str, device_id: str, device_name: str, notes: str) -> DeviceEnrollmentResult:
    url = f"{cfg.base_url}/api/enroll.php"
    payload = {
        "token": token,
        "device_id": device_id,
        "device_name": device_name,
        "notes": notes,
    }
    response = requests.post(url, json=payload, timeout=30)
    if response.status_code != 201:
        raise EnrollmentError(f"Failed to consume enrollment token: HTTP {response.status_code} {response.text[:240]}")

    data = response.json()
    return DeviceEnrollmentResult(
        device_id=str(data["device_id"]),
        api_key=str(data["api_key"]),
        channel=str(data.get("channel", "stable")),
    )


def detect_hardware_info(host: str, ssh_user: str, ssh_port: int, hat_name: Optional[str] = None) -> Dict[str, Any]:
    """
    SSH to Pi and detect hardware metadata.
    
    Returns dict with keys:
    - platform (str): 'Rpi3b+', 'Rpi4', 'Rpi5', etc.
    - memory_gb (int): Total RAM in gigabytes
    - camera_module (str): 'PiCam2', 'PiCam3', 'PiCamHQ', 'WebCam'
    - lightbox_enabled (bool): True if LightBox enabled in hwconfig
    - has_ds18b20 (bool): True if DS18B20 sensor configured
    - has_display (bool): True if display configured
    - hat_installed (str): 'Hailo', 'None', or user-provided name
    """
    
    # Step 1: Read hwconfig.py from Pi
    try:
        result = run_ssh(host, ssh_user, ssh_port, "cat ~/PyRpiCamController/CamController/hwconfig.py")
        hwconfig_text = result.stdout
    except subprocess.CalledProcessError:
        raise EnrollmentError("Could not read hwconfig.py from Pi")
    
    # Parse hwconfig: extract RpiBoard, CamChip, LightBox, Io config
    # Simple regex-based parsing for these known fields
    
    platform_match = re.search(r'"RpiBoard":\s*"([^"]+)"', hwconfig_text)
    camera_match = re.search(r'"CamChip":\s*"([^"]+)"', hwconfig_text)
    lightbox_match = re.search(r'"LightBox":\s*(True|False)', hwconfig_text)
    
    platform_from_hwconfig = platform_match.group(1) if platform_match else "Unknown"

    # Detect actual Raspberry Pi model from system (more accurate than hwconfig)
    try:
        model_result = run_ssh(host, ssh_user, ssh_port, "tr -d '\\0' </proc/device-tree/model")
        model_text = model_result.stdout.strip().lower()
        if "raspberry pi 5" in model_text:
            platform = "Rpi5"
        elif "raspberry pi 4" in model_text:
            platform = "Rpi4"
        elif "raspberry pi 3 model b plus" in model_text:
            platform = "Rpi3B+"
        elif "raspberry pi 3 model b" in model_text:
            platform = "Rpi3B"
        elif "raspberry pi zero 2" in model_text:
            platform = "RpiZero2"
        elif "raspberry pi zero" in model_text:
            platform = "RpiZero"
        else:
            platform = platform_from_hwconfig
    except subprocess.CalledProcessError:
        platform = platform_from_hwconfig

    camera = camera_match.group(1) if camera_match else "Unknown"
    lightbox = lightbox_match.group(1).lower() == "true" if lightbox_match else False
    
    # Check for DS18B20: look for ds18b20pin in Io config (not None means configured)
    # Search for the pattern "ds18b20pin": <number> or "ds18b20pin": None
    ds18b20_match = re.search(r'"ds18b20pin":\s*([^,}\n]+)', hwconfig_text)
    has_ds18b20 = False
    if ds18b20_match:
        pin_value = ds18b20_match.group(1).strip()
        has_ds18b20 = pin_value != "None" and pin_value.isdigit()
    
    # Check for display: look for displaycontrolgpio (if present and not None, it's configured)
    display_match = re.search(r'"displaycontrolgpio":\s*([^,}\n]+)', hwconfig_text)
    has_display = False
    if display_match:
        pin_value = display_match.group(1).strip()
        has_display = pin_value != "None" and pin_value.isdigit()
    
    # Step 2: Get RAM from /proc/meminfo
    try:
        result = run_ssh(host, ssh_user, ssh_port, "grep MemTotal /proc/meminfo | awk '{print $2}'")
        memory_kb = int(result.stdout.strip())
        memory_gb = max(1, (memory_kb + 524288) // (1024 * 1024))  # Round to nearest GB, min 1GB
    except (subprocess.CalledProcessError, ValueError):
        memory_gb = None
    
    # Step 3: Determine HAT (user input or default)
    if hat_name:
        hat = hat_name
    else:
        hat = "None"
    
    return {
        "platform": platform,
        "memory_gb": memory_gb,
        "camera_module": camera,
        "hat_installed": hat,
        "lightbox_enabled": lightbox,
        "has_ds18b20": has_ds18b20,
        "has_display": has_display,
    }


def report_hardware_info(
    cfg: BackendConfig,
    device_id: str,
    api_key: str,
    hardware: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Report hardware metadata to backend via /api/hardware_info endpoint.
    
    Requires device authentication (device_id + api_key).
    Returns response JSON.
    """
    url = f"{cfg.base_url}/api/hardware_info.php"
    payload = {
        "device_id": device_id,
        "api_key": api_key,
        "hardware": hardware,
    }
    response = requests.post(url, json=payload, timeout=30)
    
    if response.status_code != 200:
        raise EnrollmentError(f"Failed to report hardware info: HTTP {response.status_code} {response.text[:240]}")
    
    return response.json()


def build_remote_settings_script(payload_b64: str) -> str:
    return f"""python3 - <<'PY'
import base64
import json
from Settings.settings_manager import settings_manager

payload = json.loads(base64.b64decode('{payload_b64}').decode('utf-8'))

settings_manager.set('OtaEnable', True, save=False)
settings_manager.set('OTA.server_url', payload['server_url'], save=False)
settings_manager.set(
    'OTA.api_key',
    payload['api_key'],
    save=False,
    allow_readonly=True,
)
settings_manager.set('UpdateGroup', payload['update_group'], save=False)
settings_manager.set('TestDevice', bool(payload['test_device']), save=False)

if payload.get('device_name'):
    settings_manager.set('DeviceName', payload['device_name'], save=False)

settings_manager.save_user_settings()
print('OK: settings updated')
PY"""


def push_settings_to_pi(
    host: str,
    ssh_user: str,
    ssh_port: int,
    api_key: str,
    server_url: str,
    update_group: str,
    test_device: bool,
    device_name: str,
) -> None:
    payload = {
        "api_key": api_key,
        "server_url": server_url,
        "update_group": update_group,
        "test_device": test_device,
        "device_name": device_name,
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    remote_cmd = build_remote_settings_script(payload_b64)
    run_ssh(host, ssh_user, ssh_port, f"cd /home/pi/PyRpiCamController && {remote_cmd}")


def restart_remote_services(host: str, ssh_user: str, ssh_port: int) -> None:
    run_ssh(host, ssh_user, ssh_port, "sudo systemctl daemon-reload", capture=False)
    run_ssh(host, ssh_user, ssh_port, "sudo systemctl restart camcontroller-update.service", capture=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Securely enroll a real Pi into OTA backend")
    parser.add_argument("--host", required=True, help="Pi hostname or IP")
    parser.add_argument("--ssh-user", default="pi", help="SSH user on Pi (default: pi)")
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--ssh-key", default=None, help="Path to SSH private key file (skips password prompt)")

    parser.add_argument("--name", default="", help="Friendly device name")
    parser.add_argument("--location", default="", help="Location/note shown in admin")
    parser.add_argument("--channel", choices=["stable", "testing", "beta"], default="stable", help="OTA channel in backend")
    parser.add_argument("--update-group", choices=["production", "beta", "development"], default="production", help="Local settings update group")
    parser.add_argument("--test-device", action="store_true", help="Mark device as test device in local settings")

    parser.add_argument("--hat-name", default=None, help="HAT/accessory name (e.g. 'Hailo', 'None', or custom) (optional)")

    parser.add_argument("--ota-base-url", default=DEFAULT_OTA_BASE, help="OTA backend base URL")
    parser.add_argument("--ota-server-url", default=f"{DEFAULT_OTA_BASE}", help="Server URL written into Pi settings")
    parser.add_argument("--admin-username", default=os.environ.get("OTA_ADMIN_USERNAME", "admin"), help="OTA admin username")
    parser.add_argument("--admin-password", default=os.environ.get("OTA_ADMIN_PASSWORD", ""), help="OTA admin password (or use OTA_ADMIN_PASSWORD env)")

    parser.add_argument("--token-ttl", type=int, default=10, help="Enrollment token lifetime in minutes (1-120)")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    admin_password = args.admin_password or getpass.getpass("OTA admin password: ")
    if not admin_password:
        print("ERROR: Admin password is required", file=sys.stderr)
        return 2

    cfg = BackendConfig(
        base_url=args.ota_base_url.rstrip("/"),
        username=args.admin_username,
        password=admin_password,
    )

    try:
        print("[0/7] Opening SSH session (password prompt once)...")
        setup_ssh_session(args.host, args.ssh_user, args.ssh_port, identity_file=args.ssh_key)

        print("[1/7] Reading CPU serial from Pi over SSH...")
        cpu_id_raw = get_remote_cpu_serial(args.host, args.ssh_user, args.ssh_port)
        cpu_id = normalize_cpu_id(cpu_id_raw)
        print(f"      CPU ID: {cpu_id}")

        device_name = args.name.strip() or f"Cam-{cpu_id[-8:]}"
        notes = args.location.strip()

        print("[2/7] Detecting hardware configuration from Pi...")
        hardware = detect_hardware_info(args.host, args.ssh_user, args.ssh_port, hat_name=args.hat_name)
        print(f"      Platform: {hardware['platform']}")
        print(f"      Memory: {hardware['memory_gb']}GB")
        print(f"      Camera: {hardware['camera_module']}")
        print(f"      HAT: {hardware['hat_installed']}")
        print(f"      Features: Light={hardware['lightbox_enabled']}, DS18B20={hardware['has_ds18b20']}, Display={hardware['has_display']}")

        print("[3/7] Authenticating to OTA admin backend...")
        session = requests.Session()
        admin_login(session, cfg)

        print("[4/7] Creating one-time enrollment token...")
        token = create_enrollment_token(
            session=session,
            cfg=cfg,
            device_id=cpu_id,
            name=device_name,
            channel=args.channel,
            notes=notes,
            ttl_minutes=args.token_ttl,
        )

        print("[5/7] Consuming token via public enroll endpoint...")
        reg = consume_enrollment_token(cfg, token, cpu_id, device_name, notes)

        print("[6/7] Reporting hardware metadata to backend...")
        try:
            hw_response = report_hardware_info(cfg, cpu_id, reg.api_key, hardware)
            print(f"      ✓ Hardware recorded: {hw_response.get('message', 'OK')}")
        except EnrollmentError as hw_exc:
            print(f"      ⚠ Hardware metadata report failed: {hw_exc}")
            print("      ⚠ Continuing enrollment without hardware metadata update")

        print("[7/7] Writing OTA settings and restarting service on Pi...")
        push_settings_to_pi(
            host=args.host,
            ssh_user=args.ssh_user,
            ssh_port=args.ssh_port,
            api_key=reg.api_key,
            server_url=args.ota_server_url,
            update_group=args.update_group,
            test_device=args.test_device,
            device_name=device_name,
        )
        restart_remote_services(args.host, args.ssh_user, args.ssh_port)

        print("✅ Secure enrollment completed successfully")
        print("   ═══════════════════════════════════════════════════")
        print(f"   Host: {args.host}")
        print(f"   CPU ID: {reg.device_id}")
        print(f"   Name: {device_name}")
        print(f"   Backend channel: {reg.channel}")
        print(f"   Local update group: {args.update_group}")
        print(f"   Hardware: {hardware['platform']} / {hardware['camera_module']} / {hardware['memory_gb']}GB RAM")
        print("   ═══════════════════════════════════════════════════")
        close_ssh_session(args.host, args.ssh_user, args.ssh_port)
        return 0

    except EnrollmentError as exc:
        close_ssh_session(args.host, args.ssh_user, args.ssh_port)
        print(f"❌ Enrollment failed: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        close_ssh_session(args.host, args.ssh_user, args.ssh_port)
        stderr = (exc.stderr or "").strip()
        suffix = f"\n{stderr}" if stderr else ""
        print(
            f"❌ Remote enrollment command failed with exit code {exc.returncode}{suffix}",
            file=sys.stderr,
        )
        return 1
    except requests.RequestException as exc:
        close_ssh_session(args.host, args.ssh_user, args.ssh_port)
        print(f"❌ Network/API error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
