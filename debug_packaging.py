#!/usr/bin/env python3
"""
Debug release packaging to see what's being included
"""
from pathlib import Path

PROJECT_ROOT = Path("/home/psk/Dropbox/dev/PyRpiCamController")

include_patterns = [
    "CamController/",
    "Settings/", 
    "Services/",
    "tools/",
    "WebGui/",
    "Updates/",
    "backend/",
    "_doc/",
    "VERSION",
    "LICENSE", 
    "readme.adoc"
]

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

print("Checking include patterns:")
total_files = 0

for pattern in include_patterns:
    path = PROJECT_ROOT / pattern
    print(f"\n{pattern} -> {path}")
    print(f"  Exists: {path.exists()}")
    print(f"  Is file: {path.is_file()}")
    print(f"  Is dir: {path.is_dir()}")
    
    if path.is_file():
        print(f"  Would include file: {pattern}")
        total_files += 1
    elif path.is_dir():
        files_in_dir = list(path.rglob('*'))
        files_count = len([f for f in files_in_dir if f.is_file()])
        print(f"  Files in directory: {files_count}")
        total_files += files_count
        
        # Show first few files as example
        for i, file_path in enumerate(files_in_dir[:5]):
            if file_path.is_file():
                arcname = file_path.relative_to(PROJECT_ROOT)
                print(f"    Example: {arcname}")

print(f"\nTotal files to include: {total_files}")