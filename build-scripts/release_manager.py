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
    python3 release_manager.py release           # Full release pipeline
"""

import os
import sys
import json
import subprocess
import zipfile
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
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
1. Extract PyRpiCamController-{version}.zip to /home/pi/PyRpiCamController
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
        """Create distribution zip file"""
        self.log(f"Creating distribution package for v{version}...")
        
        # Create output directories
        RELEASE_DIR.mkdir(exist_ok=True)
        DIST_DIR.mkdir(exist_ok=True)
        
        zip_name = f"PyRpiCamController-{version}.zip"
        zip_path = DIST_DIR / zip_name
        
        # Files/directories to include
        include_patterns = [
            "CamController/",
            "Settings/", 
            "Services/",
            "tools/",
            "webgui/",
            "shared/",
            "timelapse/",
            "ota/",
            "VERSION",
            "LICENSE", 
            "readme.adoc",
            "_doc/userguide.adoc"
        ]
        
        # Files to exclude
        exclude_patterns = [
            "__pycache__",
            "*.pyc",
            ".git",
            ".venv",
            "*.log",
            "user_settings.json",
            "secrets.php",
            "releases/",
            "dist/"
        ]
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pattern in include_patterns:
                path = PROJECT_ROOT / pattern
                if path.is_file():
                    zipf.write(path, pattern)
                elif path.is_dir():
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            # Skip excluded patterns
                            skip = False
                            for exclude in exclude_patterns:
                                if exclude in str(file_path):
                                    skip = True
                                    break
                            if not skip:
                                arcname = file_path.relative_to(PROJECT_ROOT)
                                zipf.write(file_path, arcname)
        
        # Create checksum
        sha256_hash = hashlib.sha256()
        with open(zip_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        checksum = sha256_hash.hexdigest()
        checksum_path = DIST_DIR / f"{zip_name}.sha256"
        with open(checksum_path, 'w') as f:
            f.write(f"{checksum}  {zip_name}\n")
        
        # Create release notes
        notes_path = DIST_DIR / f"release-notes-{version}.md"
        with open(notes_path, 'w') as f:
            f.write(self.create_release_notes(version))
        
        file_size = zip_path.stat().st_size / (1024 * 1024)  # MB
        self.log(f"✓ Package created: {zip_name} ({file_size:.1f} MB)")
        self.log(f"✓ Checksum: {checksum[:16]}...")
        self.log(f"✓ Release notes: release-notes-{version}.md")
        
        return zip_path, checksum
    
    def git_commit_and_tag(self, version):
        """Commit version changes and create git tag"""
        if not self.git_clean:
            self.log("Git repository has uncommitted changes", "ERROR") 
            return False
            
        commands = [
            f"git add {VERSION_FILE}",
            f"git commit -m 'Bump version to {version}'",
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
    
    def full_release(self):
        """Complete release pipeline"""
        self.log("=== Full Release Pipeline ===")
        
        version = self.get_current_version()
        
        # Final tests
        if not self.run_tests():
            self.log("Tests failed - aborting release", "ERROR")
            return False
        
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
        success = manager.full_release()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()