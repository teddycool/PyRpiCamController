#!/usr/bin/env python3
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

# Simplified Install-script for PyRpiCamController - One-time installation
# 
# Key features:
# - Simple one-time installation per Pi
# - Batched package installations for efficiency
# - Progress indicators with timing
# - Better error handling and recovery
# - Automatic configuration of all services
#
# Typical installation time: 15-30 minutes

import os
import time
import subprocess
import sys
import argparse
from pathlib import Path

# Configuration
PROJECT_ROOT = "/home/pi/PyRpiCamController"

def log_step(step, message):
    """Log installation step with timing"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {step}: {message}")

def run_cmd(cmd, capture=False, check=True):
    """Run command with better error handling and optional output capture"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return result.returncode == 0
    except subprocess.CalledProcessError as e:
        log_step("ERROR", f"Command failed: {cmd}")
        log_step("ERROR", f"Error: {e}")
        return False

def get_serial():
    """Extract serial from cpuinfo file and return only the second half"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    full_serial = line.split(':')[1].strip().lstrip("0")
                    # Return only the second half of the serial for shorter hostname
                    half_length = len(full_serial) // 2
                    return full_serial[half_length:]
    except:
        pass
    return "ERROR000000000"

def detect_model():
    """Detect Raspberry Pi model and return detailed info"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            full_model = f.read().strip()
        
        # Extract key model info
        model_info = {
            'full_name': full_model,
            'is_pi3': 'Pi 3' in full_model,
            'is_pi4': 'Pi 4' in full_model,
            'is_pi5': 'Pi 5' in full_model,
            'memory_gb': detect_memory_size()
        }
        
        return model_info
    except:
        return {
            'full_name': "Unknown Pi Model",
            'is_pi3': False,
            'is_pi4': False,
            'is_pi5': False,
            'memory_gb': 1
        }

def detect_memory_size():
    """Detect total memory size in GB"""
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    # Extract memory in KB and convert to GB
                    mem_kb = int(line.split()[1])
                    mem_gb = round(mem_kb / 1024 / 1024)
                    return max(1, mem_gb)  # Minimum 1GB
    except:
        pass
    return 1

def setup_led_dependency():
    """Install rpi_ws281x using apt package detection with pip fallback."""
    log_step("PACKAGES", "Ensuring LED dependency (rpi_ws281x)...")

    if run_cmd("/usr/bin/python3 -c 'import rpi_ws281x'", capture=False, check=False):
        log_step("PACKAGES", "rpi_ws281x already available")
        return True

    apt_candidates = ["python3-rpi-ws281x", "python3-ws281x"]
    for pkg in apt_candidates:
        if run_cmd(f"apt-cache show {pkg} >/dev/null 2>&1", check=False):
            log_step("PACKAGES", f"Installing {pkg} via apt...")
            run_cmd(f"sudo apt-get install -y --no-install-recommends {pkg}", check=False)
            if run_cmd("/usr/bin/python3 -c 'import rpi_ws281x'", capture=False, check=False):
                log_step("PACKAGES", "rpi_ws281x installed successfully")
                return True

    log_step("PACKAGES", "Apt package unavailable, installing build deps for pip fallback...")
    run_cmd("sudo apt-get install -y --no-install-recommends python3-dev build-essential", check=False)

    log_step("PACKAGES", "Trying pip fallback for rpi-ws281x...")
    run_cmd("sudo /usr/bin/python3 -m pip install --break-system-packages rpi-ws281x", check=False)

    if run_cmd("/usr/bin/python3 -c 'import rpi_ws281x'", capture=False, check=False):
        log_step("PACKAGES", "rpi_ws281x installed successfully")
        return True

    log_step("WARNING", "Failed to install rpi_ws281x - LED functionality will be disabled")
    return False

def package_install(with_opencv=False):
    """Install all required packages efficiently"""
    log_step("PACKAGES", "Starting package installation...")
    
    # Detect Pi model for any model-specific adjustments
    model_info = detect_model()
    log_step("PACKAGES", f"Detected: {model_info['full_name']}")
    
    # Check available memory and setup swap if needed
    if model_info['memory_gb'] <= 1:
        log_step("PACKAGES", "Low memory detected - checking swap...")
        swap_size = run_cmd("free -m | awk '/^Swap:/ {print $2}'", capture=True)
        if swap_size and int(swap_size) < 512:
            log_step("PACKAGES", "Setting up temporary swap for installation...")
            run_cmd("sudo dphys-swapfile swapoff", check=False)
            run_cmd("sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile", check=False)
            run_cmd("sudo dphys-swapfile setup", check=False)
            run_cmd("sudo dphys-swapfile swapon", check=False)
    
    # Update package lists
    log_step("PACKAGES", "Updating package lists...")
    if not run_cmd("sudo apt-get update -y"):
        log_step("ERROR", "Failed to update package lists")
        return False
    
    # Install all APT packages in one batch
    apt_packages = [
        "python3-pip", "python3-picamera2", "libcamera-apps", "python3-libcamera",
        "python3-lgpio", "python3-rpi.gpio", "python3-numpy",
        "python3-opencv", "opencv-data",
        "ffmpeg", "gunicorn", "python3-setuptools", "python3-wheel", "python3-dev", "build-essential"
    ]

    if with_opencv:
        pass  # opencv now always installed above
    
    package_list = " ".join(apt_packages)
    install_cmd = f"sudo apt-get install -y --no-install-recommends {package_list}"
    
    log_step("PACKAGES", f"Installing {len(apt_packages)} packages in batch...")
    if not run_cmd(install_cmd):
        log_step("ERROR", "Failed to install APT packages")
        return False
    
    # Install Python packages from requirements file
    requirements_file = Path(PROJECT_ROOT) / "tools" / "requirements.txt"
    if not requirements_file.exists():
        log_step("ERROR", f"Requirements file not found: {requirements_file}")
        return False

    log_step("PACKAGES", f"Installing Python packages from {requirements_file}...")
    pip_cmd = f"sudo pip3 install --break-system-packages -r {requirements_file}"
    if not run_cmd(pip_cmd, check=False):
        log_step("WARNING", "pip requirements installation reported errors")

    setup_led_dependency()
    
    return True

def setup_comitup():
    """Setup ComitUp WiFi management"""
    log_step("COMITUP", "Setting up ComitUp WiFi management...")
    
    # Check if config file exists
    comitup_conf_source = f"{PROJECT_ROOT}/Services/comitup.conf"
    if not os.path.exists(comitup_conf_source):
        log_step("WARNING", f"ComitUp config not found at {comitup_conf_source}")
        comitup_conf_source = None
    
    # Download and install ComitUp repository package
    comitup_deb = "davesteele-comitup-apt-source_1.3_all.deb"
    download_cmd = f"wget -O /tmp/{comitup_deb} https://davesteele.github.io/comitup/deb/{comitup_deb}"
    
    log_step("COMITUP", "Downloading ComitUp package...")
    if not run_cmd(download_cmd, check=False):
        log_step("WARNING", "Failed to download ComitUp - skipping WiFi management setup")
        return False
    
    if not run_cmd(f"sudo dpkg -i /tmp/{comitup_deb}", check=False):
        log_step("WARNING", "Failed to install ComitUp repository")
        return False
    
    # Update package lists and install ComitUp + NetworkManager runtime
    log_step("COMITUP", "Installing ComitUp packages...")
    run_cmd("sudo apt-get update")
    if not run_cmd("sudo apt-get install -y --no-install-recommends network-manager comitup comitup-watch", check=False):
        log_step("WARNING", "Failed to install ComitUp packages")
        return False
    
    # Copy configuration if available
    if comitup_conf_source:
        log_step("COMITUP", "Installing ComitUp configuration...")
        run_cmd(f"sudo cp {comitup_conf_source} /etc/comitup.conf")
    
    # Configure network services
    log_step("COMITUP", "Configuring network services...")
    services_to_mask = ["dnsmasq.service", "dhcpcd.service"]
    for service in services_to_mask:
        run_cmd(f"sudo systemctl stop {service}", check=False)
        run_cmd(f"sudo systemctl disable {service}", check=False)
        run_cmd(f"sudo systemctl mask {service}", check=False)

    # Undo older masking from previous installer runs.
    run_cmd("sudo systemctl unmask wpa_supplicant.service", check=False)

    # Ensure NetworkManager manages interfaces including wlan0.
    nm_conf = """[main]
plugins=ifupdown,keyfile

[ifupdown]
managed=true

[device]
wifi.scan-rand-mac-address=no
"""
    run_cmd("sudo mkdir -p /etc/NetworkManager", check=False)
    run_cmd("sudo tee /etc/NetworkManager/NetworkManager.conf >/dev/null <<'EOF'\n" + nm_conf + "EOF", check=False)

    # Ensure comitup starts after NetworkManager and hardware init settles.
    override_conf = """[Unit]
After=NetworkManager.service network-online.target
Wants=NetworkManager.service

[Service]
Restart=on-failure
RestartSec=5
ExecStartPre=/bin/sleep 5
"""
    run_cmd("sudo mkdir -p /etc/systemd/system/comitup.service.d", check=False)
    run_cmd("sudo tee /etc/systemd/system/comitup.service.d/override.conf >/dev/null <<'EOF'\n" + override_conf + "EOF", check=False)

    # Bring up required services in correct order.
    run_cmd("sudo rfkill unblock wifi", check=False)
    run_cmd("sudo systemctl daemon-reload", check=False)
    run_cmd("sudo systemctl enable NetworkManager.service", check=False)
    run_cmd("sudo systemctl restart NetworkManager.service", check=False)
    run_cmd("sudo systemctl enable comitup.service", check=False)
    run_cmd("sudo systemctl restart comitup.service", check=False)
    
    run_cmd("sudo systemctl enable ssh", check=False)

    nm_state = run_cmd("systemctl is-active NetworkManager.service", capture=True, check=False) or "unknown"
    cu_state = run_cmd("systemctl is-active comitup.service", capture=True, check=False) or "unknown"
    log_step("COMITUP", f"Service states: NetworkManager={nm_state}, comitup={cu_state}")
    
    return True

def setup_directories():
    """Create all needed directories"""
    log_step("DIRS", "Creating directory structure...")
    
    directories = [
        "/home/pi/shared",
        "/home/pi/shared/images", 
        "/home/pi/shared/logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        os.chmod(directory, 0o755)
    
    run_cmd("sudo chown -R pi:pi /home/pi/shared")

def setup_samba():
    """Setup Samba file sharing"""
    log_step("SAMBA", "Setting up Samba file sharing...")
    
    # Install Samba packages only when this feature is enabled.
    if not run_cmd("sudo apt-get install -y --no-install-recommends samba samba-common-bin smbclient avahi-daemon libnss-mdns", check=False):
        log_step("WARNING", "Samba packages failed to install")
        return False

    # wsdd improves SMB discovery on modern Windows systems when available.
    run_cmd("sudo apt-get install -y --no-install-recommends wsdd", check=False)

    # Copy Samba configuration
    smb_conf_source = f"{PROJECT_ROOT}/Services/smb.conf"
    if os.path.exists(smb_conf_source):
        run_cmd(f"sudo cp {smb_conf_source} /etc/samba/smb.conf")
        log_step("SAMBA", "Samba configuration installed")
    else:
        log_step("WARNING", "Samba config not found - using default configuration")
        return False
    
    # Enable and start Samba services
    run_cmd("sudo systemctl enable smbd nmbd avahi-daemon", check=False)
    run_cmd("sudo systemctl restart smbd nmbd avahi-daemon", check=False)
    run_cmd("sudo systemctl enable wsdd", check=False)
    run_cmd("sudo systemctl restart wsdd", check=False)
    
    return True

def setup_services():
    """Setup all systemd services"""
    log_step("SERVICES", "Setting up system services...")
    
    services = [
        ("camcontroller.service", "CamController/camcontroller.service"),
        ("camcontroller-web.service", "WebGui/camcontroller-web.service"),
        ("camcontroller-update.service", "Updates/camcontroller-update.service")
    ]
    
    for service_name, service_path in services:
        source_path = f"{PROJECT_ROOT}/{service_path}"
        if os.path.exists(source_path):
            log_step("SERVICES", f"Installing {service_name}...")
            run_cmd(f"sudo cp {source_path} /etc/systemd/system/")
            run_cmd(f"sudo systemctl enable {service_name}")
        else:
            log_step("WARNING", f"Service file not found: {source_path}")
    
    # Reload systemd daemon
    run_cmd("sudo systemctl daemon-reload")

def sync_hostname_in_hosts(hostname):
    """Ensure /etc/hosts contains a local mapping for the configured hostname."""
    log_step("HOSTNAME", f"Syncing /etc/hosts mapping for {hostname}...")

    # Keep a backup for recovery if the hosts update fails.
    run_cmd("sudo cp /etc/hosts /etc/hosts.bak", check=False)

    existing_entry = run_cmd("grep -E '^127\\.0\\.1\\.1[[:space:]]+' /etc/hosts | head -n1", capture=True, check=False)
    if existing_entry:
        run_cmd(f"sudo sed -i 's/^127\\.0\\.1\\.1[[:space:]]\+.*/127.0.1.1 {hostname}/' /etc/hosts", check=False)
    else:
        run_cmd(f"echo '127.0.1.1 {hostname}' | sudo tee -a /etc/hosts >/dev/null", check=False)

    resolved = run_cmd(f"getent hosts {hostname}", capture=True, check=False)
    if resolved:
        log_step("HOSTNAME", f"Host resolution OK: {resolved}")
    else:
        log_step("WARNING", f"Hostname {hostname} not resolvable via /etc/hosts")

def main():
    """Main installation routine"""
    start_time = time.time()
    
    parser = argparse.ArgumentParser(description="Install PyRpiCamController on Raspberry Pi")
    parser.add_argument(
        "--with-opencv",
        action="store_true",
        help="(Deprecated - OpenCV is now always installed)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PyRpiCamController - Installation")
    print("OpenCV install: enabled (required)")
    print("ComitUp setup: enabled")
    print("Samba setup: enabled")
    print("=" * 60)
    
    # Detect Pi model
    model_info = detect_model()
    print(f"Pi Model: {model_info['full_name']}")
    print(f"Memory: {model_info['memory_gb']}GB")
    print(f"Serial: {get_serial()}")
    print("=" * 60)
    
    try:
        # Pre-flight checks
        log_step("CHECK", "Verifying project deployment...")
        
        if not os.path.exists(PROJECT_ROOT):
            print(f"ERROR: Project not found at {PROJECT_ROOT}")
            print("Please deploy the project first:")
            print(f"git clone https://github.com/teddycool/PyRpiCamController.git {PROJECT_ROOT}")
            sys.exit(1)
        
        required_dirs = ["CamController", "Settings", "WebGui", "Services"]
        for dir_name in required_dirs:
            if not os.path.exists(f"{PROJECT_ROOT}/{dir_name}"):
                print(f"ERROR: Required directory missing: {dir_name}")
                sys.exit(1)
        
        log_step("CHECK", "Project deployment verified ✓")
        
        # Package installation
        if not package_install(with_opencv=args.with_opencv):
            log_step("ERROR", "Package installation failed!")
            sys.exit(1)
        
        # ComitUp setup
        setup_comitup()
        
        # Directory structure
        setup_directories()
        
        # Samba setup
        setup_samba()
        
        # Services setup
        setup_services()
        
        # Set hostname
        hostname = get_serial()
        run_cmd(f"sudo hostnamectl set-hostname {hostname}")
        sync_hostname_in_hosts(hostname)
        log_step("HOSTNAME", f"Hostname set to: {hostname}")
        
        # Installation completed
        end_time = time.time()
        install_duration = int(end_time - start_time)
        
        print("\\n" + "=" * 60)
        print("INSTALLATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Total time: {install_duration} seconds ({install_duration//60}m {install_duration%60}s)")
        print(f"Hostname: {hostname}.local")
        print(f"Web interface: http://{hostname}.local:8080")
        print(f"Samba share: \\\\{hostname}.local\\shared")
        print("\\nNext steps:")
        print("1. Reboot to activate all services")
        print("2. Configure WiFi via ComitUp portal")
        print("3. Access web interface for camera settings")
        print("=" * 60)
            
    except KeyboardInterrupt:
        log_step("INTERRUPT", "Installation interrupted by user")
        sys.exit(0)
    except Exception as e:
        log_step("ERROR", f"Installation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()