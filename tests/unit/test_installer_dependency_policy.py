"""Tests for the Raspberry Pi Python package ownership policy."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_pi_requirements_exclude_apt_camera_stack():
    requirements = (PROJECT_ROOT / "requirements-pi.txt").read_text(encoding="utf-8")
    package_names = {
        line.split(";", 1)[0].split("=", 1)[0].split("<", 1)[0].strip().lower()
        for line in requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert package_names.isdisjoint(
        {"numpy", "opencv-python", "simplejpeg", "picamera", "picamera2"}
    )


def test_installer_uses_pi_requirements_and_checks_camera_imports():
    installer = (PROJECT_ROOT / "tools" / "install-all-optimized.py").read_text(
        encoding="utf-8"
    )

    assert '"requirements-pi.txt"' in installer
    assert '"python3-simplejpeg"' in installer
    assert "import numpy, cv2, simplejpeg" in installer
    assert "from picamera2 import Picamera2" in installer
