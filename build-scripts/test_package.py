#!/usr/bin/env python3
"""
Fixed version of release manager packaging function
"""
import zipfile
import hashlib
from pathlib import Path

PROJECT_ROOT = Path("/home/psk/Dropbox/dev/PyRpiCamController")
DIST_DIR = PROJECT_ROOT / "build-scripts" / "dist"
VERSION = "1.0.1"

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
    "LICENSE", 
    "readme.adoc"
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

zip_name = f"PyRpiCamController-{VERSION}.zip"
zip_path = DIST_DIR / zip_name

print(f"Creating package: {zip_path}")

files_added = 0
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for pattern in include_patterns:
        path = PROJECT_ROOT / pattern
        print(f"\nProcessing {pattern}...")
        
        if path.is_file():
            print(f"  Adding file: {pattern}")
            zipf.write(path, pattern)
            files_added += 1
        elif path.is_dir():
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    # Skip excluded patterns
                    skip = False
                    for exclude in exclude_patterns:
                        if exclude in str(file_path):
                            skip = True
                            print(f"  Skipping (excluded): {file_path.relative_to(PROJECT_ROOT)} [matches {exclude}]")
                            break
                    
                    if not skip:
                        arcname = file_path.relative_to(PROJECT_ROOT)
                        print(f"  Adding: {arcname}")
                        zipf.write(file_path, arcname)
                        files_added += 1
        else:
            print(f"  WARNING: {pattern} not found")

print(f"\nTotal files added: {files_added}")
print(f"Package created: {zip_path}")

# Check final size
size_mb = zip_path.stat().st_size / (1024 * 1024)
print(f"Package size: {size_mb:.1f} MB")