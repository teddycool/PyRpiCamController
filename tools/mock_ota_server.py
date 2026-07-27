#!/usr/bin/env python3
"""
Mock OTA Server for local end-to-end testing.

Simulates the sensorwebben.se PHP/MySQL backend so you can run a complete
OTA roundtrip on the Pi (or locally) without touching the real server.

Usage:
    # 1. Build a release first
    python3 build-scripts/release_manager.py build

    # 2. Start this server on your dev machine
    python3 tools/mock_ota_server.py --version 1.2.3

    # 3. On the Pi, point OTA at this machine:
    #    OTA.server_url = http://<your-lan-ip>:8765
    #    OtaEnable = true
    #    OTA.api_key = test-key

    # 4. Trigger a check from the Pi web UI or:
    #    python3 Updates/camcontroller_update_manager.py

Flags:
    --version VERSION   Version to advertise (default: reads from dist/*.tar.gz)
    --port PORT         Port to listen on (default: 8765)
    --host HOST         Bind address (default: 0.0.0.0 so Pi can reach it)
    --no-update         Respond "no update available" (tests the up-to-date path)
    --force             Set force_update=true in /check response
    --dist DIR          Directory containing the .tar.gz (default: dist/)
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_from_directory, abort
except ImportError:
    print("Flask not installed. Run: pip install flask")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DIST = PROJECT_ROOT / "dist"

log = logging.getLogger("mock_ota")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

app = Flask(__name__)

# ── Shared state (set in main) ────────────────────────────────────────────────
STATE = {
    "version": None,
    "tarball_path": None,
    "checksum": None,
    "file_size": None,
    "no_update": False,
    "force_update": False,
    "dist_dir": DEFAULT_DIST,
    "reports": [],          # accumulate POST /api/ota/report payloads
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_tarball(dist_dir: Path, version: str | None):
    """Return (version, path) for the best available tarball."""
    if version:
        p = dist_dir / f"PyRpiCamController-{version}.tar.gz"
        if p.exists():
            return version, p
        # Fallback: any tarball whose name contains the version
        for p in dist_dir.glob("*.tar.gz"):
            if version in p.name:
                return version, p
        raise FileNotFoundError(
            f"No tarball found for version {version} in {dist_dir}\n"
            f"Run: python3 build-scripts/release_manager.py build"
        )

    # Auto-detect newest tarball
    tarballs = sorted(dist_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime)
    if not tarballs:
        raise FileNotFoundError(
            f"No .tar.gz found in {dist_dir}.\n"
            f"Run: python3 build-scripts/release_manager.py build"
        )
    p = tarballs[-1]
    # Extract version from filename  e.g. PyRpiCamController-1.2.3.tar.gz
    m = re.search(r"(\d+\.\d+\.\d+)", p.name)
    detected = m.group(1) if m else "unknown"
    return detected, p


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/ota/check")
def ota_check():
    """Endpoint polled by UpdateManager.check_for_updates()"""
    cpu_id       = request.args.get("cpu_id", "unknown")
    current_ver  = request.args.get("current_version", "0.0.0")
    api_key      = request.args.get("api_key", "")

    log.info(f"CHECK  cpu={cpu_id}  current={current_ver}  key={api_key!r}")

    if STATE["no_update"]:
        resp = {"update_available": False, "current_version": current_ver}
        log.info(f"  → no_update mode: {resp}")
        return jsonify(resp)

    server_ver = STATE["version"]
    update_available = current_ver != server_ver

    if not update_available:
        resp = {"update_available": False, "current_version": current_ver}
        log.info(f"  → already up to date ({current_ver})")
        return jsonify(resp)

    # Build download URL visible to the caller (use Host header so Pi LAN IP works)
    host = request.host          # e.g. 192.168.1.42:8765
    filename = STATE["tarball_path"].name
    download_url = f"http://{host}/releases/{filename}"

    resp = {
        "update_available": True,
        "version":          server_ver,
        "download_url":     download_url,
        "checksum":         STATE["checksum"],
        "file_size":        STATE["file_size"],
        "release_notes":    f"Mock release {server_ver} — local test",
        "force_update":     STATE["force_update"],
        "min_version":      "0.0.0",
    }
    log.info(f"  → UPDATE {current_ver} → {server_ver}  url={download_url}")
    return jsonify(resp)


@app.route("/releases/<path:filename>")
def serve_release(filename):
    """Serve the tarball for download by the Pi."""
    dist_dir = STATE["dist_dir"]
    target = dist_dir / filename
    if not target.exists():
        log.warning(f"DOWNLOAD 404: {filename}")
        abort(404)
    log.info(f"DOWNLOAD {filename}  ({target.stat().st_size // 1024} KB)")
    return send_from_directory(str(dist_dir), filename)


@app.route("/api/ota/report", methods=["POST"])
def ota_report():
    """Receive status reports from the Pi after install attempt."""
    payload = request.get_json(silent=True) or {}
    payload["_received_at"] = datetime.utcnow().isoformat()
    STATE["reports"].append(payload)

    status      = payload.get("status", "?")
    cpu_id      = payload.get("cpu_id", "?")
    to_version  = payload.get("to_version", "?")
    error       = payload.get("error_message", "")

    if status == "success":
        log.info(f"REPORT ✓ cpu={cpu_id} updated to {to_version}")
    else:
        log.warning(f"REPORT ✗ cpu={cpu_id} status={status} error={error!r}")

    return jsonify({"status": "received", "ok": True}), 200


@app.route("/api/ota/reports")
def list_reports():
    """Debug endpoint: view all reports received this session."""
    return jsonify(STATE["reports"])


@app.route("/")
def index():
    return (
        "<h2>Mock OTA Server</h2>"
        f"<p>Advertising version: <b>{STATE['version']}</b></p>"
        f"<p>Tarball: <b>{STATE['tarball_path'].name if STATE['tarball_path'] else 'none'}</b></p>"
        f"<p>SHA-256: <code>{STATE['checksum']}</code></p>"
        f"<p>Reports received: <b>{len(STATE['reports'])}</b> "
        f"— <a href='/api/ota/reports'>view</a></p>"
        "<hr>"
        "<p>Endpoints:</p><ul>"
        "<li>GET /api/ota/check?cpu_id=&amp;current_version=&amp;api_key=</li>"
        "<li>GET /releases/&lt;file.tar.gz&gt;</li>"
        "<li>POST /api/ota/report  (JSON body)</li>"
        "<li>GET /api/ota/reports  (debug)</li>"
        "</ul>"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mock OTA server for local testing")
    parser.add_argument("--version", default=None,
                        help="Version to advertise (auto-detect from dist/ if omitted)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--no-update", action="store_true",
                        help="Always respond: no update available")
    parser.add_argument("--force", action="store_true",
                        help="Set force_update=true in check response")
    parser.add_argument("--dist", default=str(DEFAULT_DIST),
                        help=f"Directory with .tar.gz files (default: {DEFAULT_DIST})")
    args = parser.parse_args()

    dist_dir = Path(args.dist)
    STATE["dist_dir"]   = dist_dir
    STATE["no_update"]  = args.no_update
    STATE["force_update"] = args.force

    try:
        version, tarball = _find_tarball(dist_dir, args.version)
    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)

    # Compute real checksum and only trust sidecar if it matches.
    # This avoids hard-to-debug cases where tarball was rebuilt but sidecar is stale.
    actual_checksum = _sha256(tarball)
    sidecar = Path(str(tarball) + ".sha256")
    if sidecar.exists():
        sidecar_checksum = sidecar.read_text().split()[0]
        if sidecar_checksum == actual_checksum:
            checksum = sidecar_checksum
            log.info(f"SHA-256 loaded from sidecar: {checksum}")
        else:
            checksum = actual_checksum
            log.warning("SHA-256 sidecar mismatch detected; using computed checksum instead")
            log.warning(f"  sidecar : {sidecar_checksum}")
            log.warning(f"  computed: {actual_checksum}")
    else:
        checksum = actual_checksum
        log.info("Computed SHA-256 (no sidecar found)…")

    STATE["version"]      = version
    STATE["tarball_path"] = tarball
    STATE["checksum"]     = checksum
    STATE["file_size"]    = tarball.stat().st_size

    log.info("=" * 60)
    log.info(f"Mock OTA Server  —  http://{args.host}:{args.port}")
    log.info(f"  version  : {version}")
    log.info(f"  tarball  : {tarball.name}  ({STATE['file_size']//1024} KB)")
    log.info(f"  sha256   : {checksum}")
    log.info(f"  no-update: {STATE['no_update']}")
    log.info(f"  force    : {STATE['force_update']}")
    log.info("=" * 60)
    log.info("Pi config needed:")
    log.info(f"  OTA.server_url = http://<this-machine-LAN-IP>:{args.port}")
    log.info(f"  OTA.api_key    = test-key  (any value accepted)")
    log.info(f"  OtaEnable      = true")
    log.info("=" * 60)

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
