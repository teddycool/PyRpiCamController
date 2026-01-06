#!/usr/bin/env python3
# Package Cache Manager for PyRpiCamController
# Creates, manages, and distributes package caches for fast offline installations

import os
import json
import subprocess
import sys
import shutil
from pathlib import Path
import argparse

CACHE_DIR = "/home/pi/.pycam_install_cache"
PACKAGE_CACHE = f"{CACHE_DIR}/packages"
DOWNLOADS_CACHE = f"{CACHE_DIR}/downloads"

def run_cmd(cmd, capture=False):
    """Run command and return success status"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=True)
            return True
    except subprocess.CalledProcessError:
        return False

def create_cache():
    """Download and cache all required packages"""
    print("Creating PyRpiCamController package cache...")
    
    # Create cache directories
    os.makedirs(PACKAGE_CACHE, exist_ok=True)
    os.makedirs(DOWNLOADS_CACHE, exist_ok=True)
    
    # Define all packages
    apt_packages = [
        "python3-pip", "python3-picamera2", "libcamera-apps", "python3-libcamera",
        "python3-lgpio", "python3-rpi.gpio", "python3-opencv", "opencv-data", 
        "ffmpeg", "git", "curl", "samba", "samba-common-bin", "gunicorn"
    ]
    
    pip_packages = [
        "rpi-ws281x", "simplejpeg", "requests", "flask"
    ]
    
    # Update package lists
    print("Updating package lists...")
    run_cmd("sudo apt-get update")
    
    # Download APT packages without installing
    package_list = " ".join(apt_packages)
    print(f"Downloading {len(apt_packages)} APT packages...")
    if run_cmd(f"sudo apt-get install -d -y --no-install-recommends {package_list}"):
        # Copy to our cache
        run_cmd(f"sudo cp /var/cache/apt/archives/*.deb {PACKAGE_CACHE}/ 2>/dev/null")
        print(f"✓ APT packages cached in {PACKAGE_CACHE}")
    
    # Download ComitUp package
    print("Downloading ComitUp package...")
    comitup_url = "https://davesteele.github.io/comitup/deb/davesteele-comitup-apt-source_1.3_all.deb"
    comitup_file = f"{DOWNLOADS_CACHE}/davesteele-comitup-apt-source_1.3_all.deb"
    if run_cmd(f"wget -O {comitup_file} {comitup_url}"):
        print(f"✓ ComitUp package cached")
    
    # Download Python packages (wheels) for offline installation
    print(f"Downloading {len(pip_packages)} Python packages...")
    pip_cache_dir = f"{CACHE_DIR}/pip_packages"
    os.makedirs(pip_cache_dir, exist_ok=True)
    
    for package in pip_packages:
        print(f"  Downloading {package}...")
        run_cmd(f"pip3 download {package} --dest {pip_cache_dir}")
    
    # Save package manifest
    manifest = {
        "apt_packages": apt_packages,
        "pip_packages": pip_packages,
        "created": subprocess.check_output("date", shell=True).decode().strip(),
        "pi_model": get_pi_model(),
        "os_version": get_os_version()
    }
    
    with open(f"{CACHE_DIR}/manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Calculate cache size
    cache_size = get_directory_size(CACHE_DIR)
    print(f"\n✓ Package cache created successfully!")
    print(f"  Location: {CACHE_DIR}")
    print(f"  Size: {cache_size:.1f} MB")
    print(f"  APT packages: {len(apt_packages)}")
    print(f"  Python packages: {len(pip_packages)}")

def get_pi_model():
    """Get Raspberry Pi model"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            return f.read().strip()
    except:
        return "Unknown"

def get_os_version():
    """Get OS version"""
    try:
        return run_cmd("lsb_release -ds", capture=True)
    except:
        return "Unknown"

def get_directory_size(path):
    """Get directory size in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except:
                pass
    return total_size / (1024 * 1024)  # Convert to MB

def show_cache_info():
    """Display cache information"""
    if not os.path.exists(CACHE_DIR):
        print("No cache found. Run 'create' command first.")
        return
    
    manifest_file = f"{CACHE_DIR}/manifest.json"
    if os.path.exists(manifest_file):
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        print("PyRpiCamController Package Cache Information:")
        print("=" * 50)
        print(f"Location: {CACHE_DIR}")
        print(f"Created: {manifest.get('created', 'Unknown')}")
        print(f"Pi Model: {manifest.get('pi_model', 'Unknown')}")
        print(f"OS Version: {manifest.get('os_version', 'Unknown')}")
        print(f"Cache Size: {get_directory_size(CACHE_DIR):.1f} MB")
        print(f"APT Packages: {len(manifest.get('apt_packages', []))}")
        print(f"Python Packages: {len(manifest.get('pip_packages', []))}")
        
        print("\nCached APT Packages:")
        for pkg in manifest.get('apt_packages', []):
            print(f"  - {pkg}")
            
        print("\nCached Python Packages:")
        for pkg in manifest.get('pip_packages', []):
            print(f"  - {pkg}")
    else:
        print(f"Cache exists at {CACHE_DIR} but no manifest found.")
        print(f"Cache Size: {get_directory_size(CACHE_DIR):.1f} MB")

def export_cache(export_path):
    """Export cache to a portable archive"""
    if not os.path.exists(CACHE_DIR):
        print("No cache found. Run 'create' command first.")
        return
    
    print(f"Exporting cache to {export_path}...")
    
    # Create tar.gz archive
    if run_cmd(f"tar -czf {export_path} -C {os.path.dirname(CACHE_DIR)} {os.path.basename(CACHE_DIR)}"):
        archive_size = os.path.getsize(export_path) / (1024 * 1024)
        print(f"✓ Cache exported successfully!")
        print(f"  Archive: {export_path}")
        print(f"  Size: {archive_size:.1f} MB")
        print("\nTo use this cache on another Pi:")
        print(f"1. Copy {export_path} to the target Pi")
        print(f"2. Extract: tar -xzf {os.path.basename(export_path)} -C /home/pi/")
        print("3. Run the optimized install script")
    else:
        print("Failed to create archive")

def import_cache(archive_path):
    """Import cache from an archive"""
    if not os.path.exists(archive_path):
        print(f"Archive not found: {archive_path}")
        return
    
    print(f"Importing cache from {archive_path}...")
    
    # Remove existing cache
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    
    # Extract archive
    if run_cmd(f"tar -xzf {archive_path} -C {os.path.dirname(CACHE_DIR)}"):
        print(f"✓ Cache imported successfully to {CACHE_DIR}")
        show_cache_info()
    else:
        print("Failed to extract archive")

def clear_cache():
    """Remove all cached packages"""
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
        print("✓ Cache cleared successfully")
    else:
        print("No cache found")

def main():
    parser = argparse.ArgumentParser(description="PyRpiCamController Package Cache Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create cache command
    subparsers.add_parser('create', help='Download and create package cache')
    
    # Show info command
    subparsers.add_parser('info', help='Show cache information')
    
    # Export cache command
    export_parser = subparsers.add_parser('export', help='Export cache to archive')
    export_parser.add_argument('path', help='Output archive path (e.g., pycam_cache.tar.gz)')
    
    # Import cache command
    import_parser = subparsers.add_parser('import', help='Import cache from archive')
    import_parser.add_argument('path', help='Archive path to import')
    
    # Clear cache command
    subparsers.add_parser('clear', help='Clear all cached packages')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        create_cache()
    elif args.command == 'info':
        show_cache_info()
    elif args.command == 'export':
        export_cache(args.path)
    elif args.command == 'import':
        import_cache(args.path)
    elif args.command == 'clear':
        clear_cache()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()