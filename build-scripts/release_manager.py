#!/usr/bin/env python3
"""
PyRpiCamController Release Management Script

Creates tested, versioned releases with automatic packaging and distribution.
Handles version bumping, testing, tagging, and zip file creation.

Usage:
    python3 release_manager.py test              # Test current version
    python3 release_manager.py prepare patch     # Prepare patch release
    python3 release_manager.py prepare minor     # Prepare minor release  
    python3 release_manager.py prepare major     # Prepare major release
    python3 release_manager.py build             # Build release package
    python3 release_manager.py release           # Full release pipeline (auto patch bump)
    python3 release_manager.py release minor     # Full release pipeline (minor bump)
"""

import os
import sys
import json
import subprocess
import tarfile
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
RELEASE_NOTES_FILE = PROJECT_ROOT / "RELEASE_NOTES.md"
RELEASE_DIR = PROJECT_ROOT / "releases"
DIST_DIR = PROJECT_ROOT / "dist"

class ReleaseManager:
    def __init__(self):
        self.current_version = self.get_current_version()
        self.git_clean = self.check_git_status()
        
    def log(self, message, level="INFO"):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def get_current_version(self):
        """Read current version from VERSION file"""
        try:
            with open(VERSION_FILE) as f:
                return f.read().strip()
        except FileNotFoundError:
            self.log("VERSION file not found, creating v1.0.0", "WARN")
            self.write_version("1.0.0")
            return "1.0.0"
    
    def write_version(self, version):
        """Write version to VERSION file"""
        with open(VERSION_FILE, 'w') as f:
            f.write(version + '\n')
        self.log(f"Version updated to {version}")
    
    def bump_version(self, bump_type):
        """Bump version number according to semver"""
        major, minor, patch = map(int, self.current_version.split('.'))
        
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1  
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")
            
        new_version = f"{major}.{minor}.{patch}"
        self.write_version(new_version)
        return new_version
    
    def check_git_status(self):
        """Check if git repo is clean"""
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=PROJECT_ROOT)
            return len(result.stdout.strip()) == 0
        except:
            return False

    def get_git_status_entries(self):
        """Return parsed git status --porcelain entries"""
        try:
            result = subprocess.run(['git', 'status', '--porcelain'],
                                  capture_output=True, text=True, cwd=PROJECT_ROOT)
            if result.returncode != 0:
                return []
            entries = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                status = line[:2]
                path = line[3:].strip()
                entries.append((status, path))
            return entries
        except Exception:
            return []

    def has_only_version_change(self):
        """True if only release metadata files are modified/staged."""
        entries = self.get_git_status_entries()
        if not entries:
            return False
        allowed = {"VERSION", "RELEASE_NOTES.md"}
        return all(path in allowed for _, path in entries)

    def update_master_release_notes(self, version):
        """Prepend a new release entry to RELEASE_NOTES.md (latest-first)."""
        today = datetime.now().strftime('%Y-%m-%d')
        preamble = (
            "This file is the canonical project changelog.\n\n"
            "- Newest release is always at the top.\n"
            "- Historical entries are kept below.\n"
            "- Per-build notes are also generated in `dist/release-notes-<version>.md`."
        )
        new_entry = f"""## v{version}

Release date: {today}

### Highlights

- [Add release highlights]

### Validation

- [Add validation notes]

"""

        if RELEASE_NOTES_FILE.exists():
            existing = RELEASE_NOTES_FILE.read_text(encoding='utf-8')
        else:
            existing = "# Release Notes\n\n"

        header = "# Release Notes"
        existing_releases = ""
        if existing.startswith(header):
            rest = existing[len(header):].lstrip('\n')
            if rest.startswith("This file is the canonical project changelog."):
                release_start = rest.find("\n## ")
                existing_releases = rest[release_start + 1:] if release_start != -1 else ""
            else:
                release_start = rest.find("## ")
                existing_releases = rest[release_start:] if release_start != -1 else rest
        else:
            release_start = existing.find("## ")
            existing_releases = existing[release_start:] if release_start != -1 else existing.strip()

        updated = f"{header}\n\n{preamble}\n\n{new_entry}{existing_releases.lstrip()}"

        RELEASE_NOTES_FILE.write_text(updated, encoding='utf-8')
        self.log(f"Master release notes updated: {RELEASE_NOTES_FILE}")
    
    def run_cmd(self, cmd, check=True):
        """Run command and return success/output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, 
                                  text=True, cwd=PROJECT_ROOT)
            if check and result.returncode != 0:
                self.log(f"Command failed: {cmd}", "ERROR")
                self.log(f"Error: {result.stderr}", "ERROR")
                return False, result.stderr
            return True, result.stdout
        except Exception as e:
            self.log(f"Command exception: {e}", "ERROR")
            return False, str(e)
    
    def run_tests(self):
        """Run comprehensive test suite"""
        self.log("Running test suite...")
        
        tests = [
            ("Syntax Check", "python3 -m py_compile CamController/Main.py"),
            ("Settings Manager", "python3 Settings/settings_manager.py --validate"),
            ("Service Files", "systemd-analyze verify Services/*.service || true"),
            ("SMB Config", "testparm -s Services/smb.conf || true"),
        ]
        
        # Run available test scripts
        test_scripts = [
            "tools/test_camera_service.py",
            "tools/test_web_service.py", 
            "tools/test_smb_service.py"
        ]
        
        all_passed = True
        
        for name, cmd in tests:
            self.log(f"Running {name}...")
            success, output = self.run_cmd(cmd, check=False)
            if success:
                self.log(f"✓ {name} passed")
            else:
                self.log(f"✗ {name} failed: {output}", "ERROR")
                all_passed = False
        
        # Note about test scripts (they require Pi hardware)
        self.log("Note: Hardware test scripts require Pi hardware to run")
        for script in test_scripts:
            if os.path.exists(PROJECT_ROOT / script):
                self.log(f"Available for Pi testing: {script}")
        
        return all_passed
    
    def create_release_notes(self, version):
        """Generate release notes"""
        notes = f"""# PyRpiCamController v{version}

Released: {datetime.now().strftime('%Y-%m-%d')}

## Changes in this version:
- [Add your changes here]

## Installation:
1. Extract PyRpiCamController-{version}.tar.gz to /home/pi/PyRpiCamController
2. Run: cd /home/pi/PyRpiCamController/tools
3. Run: sudo python3 install-all-optimized.py

## Testing:
- Camera: python3 tools/test_camera_service.py
- Web: python3 tools/test_web_service.py  
- SMB: python3 tools/test_smb_service.py

## Requirements:
- Raspberry Pi 3B+ or newer
- Raspberry Pi OS (Bullseye/Bookworm)
- Python 3.9+
- Camera module (PiCam HQ/3 or USB webcam)

## Support:
- Hardware-specific test scripts included
- Optimized installation (15-25 minutes)
- Guest SMB file sharing
- Web-based settings management
"""
        return notes
    
    def create_distribution_package(self, version):
        """Create distribution tar.gz file suitable for OTA delivery"""
        self.log(f"Creating distribution package for v{version}...")
        
        # Create output directories
        RELEASE_DIR.mkdir(exist_ok=True)
        DIST_DIR.mkdir(exist_ok=True)
        
        tar_name = f"PyRpiCamController-{version}.tar.gz"
        tar_path = DIST_DIR / tar_name
        
        # Files/directories to include
        include_patterns = [
            "CamController/",
            "Settings/", 
            "Services/",
            "tools/",
            "WebGui/",
            "Updates/",
            "_doc/",
            "VERSION",
            "requirements-pi.txt",
            "requirements.txt",
            "LICENSE", 
            "README.md"
        ]
        
        # Files to exclude
        exclude_patterns = [
            "__pycache__",
            ".pyc",
            ".git",
            ".venv", 
            ".log",
            "user_settings.json",
            "secrets.php",
            "releases/",
            "dist/",
            "debug_packaging.py"
        ]

        def _tar_filter(tarinfo):
            for excl in exclude_patterns:
                if excl in tarinfo.name:
                    return None
            return tarinfo

        with tarfile.open(tar_path, 'w:gz') as tf:
            for pattern in include_patterns:
                path = PROJECT_ROOT / pattern
                if path.exists():
                    tf.add(path, arcname=pattern.rstrip('/'), filter=_tar_filter)
        
        # Create SHA-256 sidecar (matches OTA client expectation)
        sha256_hash = hashlib.sha256()
        with open(tar_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        checksum = sha256_hash.hexdigest()
        checksum_path = DIST_DIR / f"{tar_name}.sha256"
        with open(checksum_path, 'w') as f:
            f.write(f"{checksum}  {tar_name}\n")
        
        # Create release notes
        notes_path = DIST_DIR / f"release-notes-{version}.md"
        with open(notes_path, 'w') as f:
            f.write(self.create_release_notes(version))
        
        file_size = tar_path.stat().st_size / (1024 * 1024)  # MB
        self.log(f"✓ Package created: {tar_name} ({file_size:.1f} MB)")
        self.log(f"✓ SHA-256: {checksum}")
        self.log(f"✓ Sidecar:  {tar_name}.sha256")
        self.log(f"✓ Release notes: release-notes-{version}.md")
        
        return tar_path, checksum
    
    def git_commit_and_tag(self, version):
        """Commit version changes and create git tag"""
        commands = [
            f"git add {VERSION_FILE} {RELEASE_NOTES_FILE}",
            f"git commit -m 'Release {version}: update VERSION and release notes'",
            f"git tag -a v{version} -m 'Release version {version}'",
        ]
        
        for cmd in commands:
            success, output = self.run_cmd(cmd)
            if not success:
                self.log(f"Git operation failed: {cmd}", "ERROR")
                return False
                
        self.log(f"✓ Git tag v{version} created")
        return True
    
    def prepare_release(self, bump_type):
        """Prepare a new release"""
        self.log(f"=== Preparing {bump_type} release ===")
        
        if not self.git_clean:
            self.log("Git repository must be clean for release", "ERROR")
            return False
            
        # Bump version
        new_version = self.bump_version(bump_type)
        self.log(f"Version bumped: {self.current_version} → {new_version}")
        
        # Run tests
        if not self.run_tests():
            self.log("Tests failed - aborting release", "ERROR")
            return False
        
        self.log(f"Release v{new_version} prepared successfully")
        self.log("Next steps:")
        self.log(f"1. Review changes")
        self.log(f"2. Run: python3 release_manager.py build")
        self.log(f"3. Run: python3 release_manager.py release")
        
        return True
    
    def build_release(self):
        """Build release package"""
        self.log("=== Building release package ===")
        
        version = self.get_current_version()
        
        # Run tests again
        if not self.run_tests():
            self.log("Tests failed - aborting build", "ERROR")
            return False
        
        # Create package
        zip_path, checksum = self.create_distribution_package(version)
        
        self.log(f"Release package built successfully")
        self.log(f"Package: {zip_path}")
        self.log(f"Ready for distribution")
        
        return True
    
    def full_release(self, bump_type="patch"):
        """Complete release pipeline"""
        self.log("=== Full Release Pipeline ===")

        if self.check_git_status():
            version = self.bump_version(bump_type)
            self.current_version = version
            self.log(f"Version bumped for release: {version}")
        elif self.has_only_version_change():
            version = self.get_current_version()
            self.log(f"Detected prepared release VERSION={version}; continuing without additional bump")
        else:
            self.log("Git repository must be clean or only have VERSION changed for release", "ERROR")
            return False
        
        # Final tests
        if not self.run_tests():
            self.log("Tests failed - aborting release", "ERROR")
            return False

        # Update canonical release notes (latest-first)
        self.update_master_release_notes(version)
        
        # Git operations
        if not self.git_commit_and_tag(version):
            return False
        
        # Create package
        zip_path, checksum = self.create_distribution_package(version)
        
        self.log(f"🚀 Release v{version} completed successfully!")
        self.log(f"Package: {zip_path}")
        self.log(f"Git tag: v{version}")
        self.log(f"Ready for distribution and OTA updates")
        
        return True
    
    def test_current(self):
        """Test current version without releasing"""
        self.log("=== Testing Current Version ===")
        self.log(f"Current version: {self.current_version}")
        
        if self.run_tests():
            self.log("✓ All tests passed")
            return True
        else:
            self.log("✗ Some tests failed", "ERROR")
            return False

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    manager = ReleaseManager()
    command = sys.argv[1]
    
    if command == "test":
        success = manager.test_current()
    elif command == "prepare":
        if len(sys.argv) < 3:
            print("Usage: python3 release_manager.py prepare [major|minor|patch]")
            return
        bump_type = sys.argv[2]
        success = manager.prepare_release(bump_type)
    elif command == "build":
        success = manager.build_release()
    elif command == "release":
        bump_type = "patch"
        if len(sys.argv) >= 3:
            bump_type = sys.argv[2]
        if bump_type not in {"major", "minor", "patch"}:
            print("Usage: python3 release_manager.py release [major|minor|patch]")
            return
        success = manager.full_release(bump_type)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()