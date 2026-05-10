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
import logging
import json
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = "/home/pi/PyRpiCamController"

# Installation logging setup
class BufferedInstallLogger:
    """Logger that buffers messages and writes to shared directory when available"""
    
    def __init__(self):
        self.buffer = []
        self.start_time = datetime.now()
        self.shared_log_path = None
        
    def log(self, level, step, message):
        """Buffer a log message"""
        timestamp = datetime.now()
        log_record = {
            'timestamp': timestamp,
            'level': level,
            'step': step,
            'message': message,
            'console_msg': f"[{timestamp.strftime('%H:%M:%S')}] {step}: {message}"
        }
        self.buffer.append(log_record)
        
        # Print to console immediately
        print(log_record['console_msg'])
        
    def set_shared_path(self, shared_dir):
        """Set the path to shared directory and write buffered logs"""
        if shared_dir and os.path.exists(shared_dir):
            log_dir = os.path.join(shared_dir, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Create install log filename with timestamp
            log_filename = f"install_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
            self.shared_log_path = os.path.join(log_dir, log_filename)
            
            # Write all buffered logs
            self._write_buffered_logs()
            
    def _write_buffered_logs(self):
        """Write all buffered logs to the shared log file"""
        if not self.shared_log_path:
            return
            
        try:
            with open(self.shared_log_path, 'w') as f:
                # Write install session header
                header = {
                    'install_session': {
                        'start_time': self.start_time.isoformat(),
                        'hostname': os.uname().nodename,
                        'python_version': sys.version.split()[0],
                        'installer_version': '1.0'
                    }
                }
                f.write(json.dumps(header) + '\n')
                
                # Write all buffered log records in JSON format (same as main app)
                for record in self.buffer:
                    log_entry = {
                        'time': record['timestamp'].strftime('%Y-%m-%d %H:%M:%S,%f')[:-3],
                        'logname': 'install.' + record['step'].lower(),
                        'logLevel': record['level'],
                        'message': record['message']
                    }
                    f.write(json.dumps(log_entry) + '\n')
                    
        except Exception as e:
            print(f"Warning: Could not write install log to {self.shared_log_path}: {e}")
    
    def append_log(self, level, step, message):
        """Add a new log entry after shared path is set"""
        self.log(level, step, message)
        
        # If shared path is available, append immediately
        if self.shared_log_path:
            try:
                with open(self.shared_log_path, 'a') as f:
                    log_entry = {
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3],
                        'logname': 'install.' + step.lower(),
                        'logLevel': level,
                        'message': message
                    }
                    f.write(json.dumps(log_entry) + '\n')
            except:
                pass  # Don't fail installation if logging fails
    
    def finalize(self, success=True, duration=None):
        """Write final installation status"""
        status = "SUCCESS" if success else "FAILED"
        final_message = f"Installation {status}"
        if duration:
            final_message += f" - Total time: {duration} seconds ({duration//60}m {duration%60}s)"
            
        self.append_log("INFO", "INSTALL", final_message)

# Global logger instance
install_logger = BufferedInstallLogger()

def log_step(step, message, level="INFO"):
    """Log installation step with buffering"""
    install_logger.append_log(level, step, message)

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

def run_cmd_with_retry(cmd, capture=False, check=True, retries=3, retry_delay=5, timeout=None):
    """Run command with retry support for flaky network or package-manager steps."""
    for attempt in range(1, retries + 1):
        try:
            if capture:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=check,
                    timeout=timeout,
                )
                return result.stdout.strip()

            result = subprocess.run(cmd, shell=True, check=check, timeout=timeout)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            log_step("WARNING", f"Command timed out (attempt {attempt}/{retries}): {cmd}")
        except subprocess.CalledProcessError as e:
            log_step("WARNING", f"Command failed (attempt {attempt}/{retries}): {cmd}")
            log_step("WARNING", f"Error: {e}")

        if attempt < retries:
            time.sleep(retry_delay)

    return False

def recover_package_manager():
    """Try to recover apt/dpkg state after interrupted installs."""
    log_step("PACKAGES", "Attempting package manager recovery...")
    run_cmd("sudo dpkg --configure -a", check=False)
    run_cmd(
        "sudo env DEBIAN_FRONTEND=noninteractive apt-get -f install -y "
        "-o Acquire::Retries=5 -o Dpkg::Use-Pty=0",
        check=False,
    )

def run_apt_command(args, retries=3, timeout=None):
    """Run apt-get with network-friendly defaults and recovery between attempts."""
    apt_cmd = (
        "sudo env DEBIAN_FRONTEND=noninteractive apt-get "
        "-o Acquire::Retries=5 "
        "-o Acquire::http::Timeout=30 "
        "-o Acquire::https::Timeout=30 "
        "-o Dpkg::Use-Pty=0 "
        f"{args}"
    )

    for attempt in range(1, retries + 1):
        if run_cmd_with_retry(apt_cmd, check=True, retries=1, timeout=timeout):
            return True

        recover_package_manager()
        if attempt < retries:
            log_step("PACKAGES", f"Retrying apt command ({attempt + 1}/{retries})...")
            time.sleep(5)

    return False

def install_package_group(group_name, packages, retries=3, timeout=None):
    """Install one logical package group with retries and clear progress logging."""
    package_list = " ".join(packages)
    log_step("PACKAGES", f"Installing {group_name} ({len(packages)} packages)...")
    return run_apt_command(
        f"install -y --no-install-recommends --fix-missing {package_list}",
        retries=retries,
        timeout=timeout,
    )

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
    if not run_apt_command("update -y", retries=3, timeout=1800):
        log_step("ERROR", "Failed to update package lists")
        return False

    # Install APT packages in staged groups so interrupted runs can resume more cleanly.
    core_packages = [
        "python3-pip", "python3-picamera2", "libcamera-apps", "python3-libcamera",
        "python3-lgpio", "python3-rpi.gpio", "python3-numpy",
        "gunicorn", "python3-setuptools", "python3-wheel", "python3-dev", "build-essential"
    ]
    media_packages = [
        "ffmpeg",
        "python3-opencv",
        "opencv-data",
    ]

    install_plan = [("core runtime packages", core_packages)]

    # The OpenCV/media stack pulls in most dependencies and is the most sensitive on Pi 3 + slow links.
    if model_info['memory_gb'] <= 1 or model_info['is_pi3']:
        install_plan.extend([
            ("media support", ["ffmpeg"]),
            ("opencv stack", ["python3-opencv", "opencv-data"]),
        ])
    else:
        install_plan.append(("media stack", media_packages))

    for group_name, package_group in install_plan:
        if not install_package_group(group_name, package_group, retries=3, timeout=7200):
            log_step("ERROR", f"Failed to install {group_name}")
            return False
    
    # Install Python packages from requirements file
    requirements_file = Path(PROJECT_ROOT) / "requirements.txt"
    if not requirements_file.exists():
        log_step("ERROR", f"Requirements file not found: {requirements_file}")
        return False

    log_step("PACKAGES", f"Installing Python packages from {requirements_file}...")
    pip_cmd = f"sudo pip3 install --break-system-packages -r {requirements_file}"
    if not run_cmd_with_retry(pip_cmd, check=False, retries=3, timeout=3600):
        log_step("WARNING", "pip requirements installation reported errors")

    setup_led_dependency()
    
    return True

def setup_comitup():
    """Setup ComitUp WiFi management - simple version with proper repository"""
    log_step("COMITUP", "Setting up ComitUp WiFi management...")
    
    # First, configure WiFi country and unblock WiFi
    log_step("COMITUP", "Configuring WiFi country and unblocking WiFi...")
    run_cmd("sudo rfkill unblock wifi")
    
    # Set WiFi country to Sweden (SE) - adjust as needed
    # This can also be set via raspi-config non-interactively
    run_cmd('sudo raspi-config nonint do_wifi_country SE')
    
    # Alternative method if raspi-config doesn't work
    run_cmd('echo "country=SE" | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf', check=False)
    
    # Add ComitUp repository
    log_step("COMITUP", "Adding ComitUp repository...")
    comitup_deb = "davesteele-comitup-apt-source_1.3_all.deb"
    if not run_cmd(f"wget -O /tmp/{comitup_deb} https://davesteele.github.io/comitup/deb/{comitup_deb}", check=False):
        log_step("WARNING", "Failed to download ComitUp repository - skipping WiFi management setup")
        return False
    
    if not run_cmd(f"sudo dpkg -i /tmp/{comitup_deb}", check=False):
        log_step("WARNING", "Failed to install ComitUp repository")
        return False
    
    # Update package lists and install ComitUp
    log_step("COMITUP", "Installing ComitUp...")
    run_cmd("sudo apt-get update")
    if not run_cmd("sudo apt-get install -y comitup"):
        log_step("WARNING", "Failed to install ComitUp - skipping WiFi management setup")
        return False
    
    # Generate dynamic configuration with hostname-based AP name
    log_step("COMITUP", "Creating ComitUp configuration...")
    hostname = get_serial()
    
    comitup_config = f"""#
# Comitup configuration
#

# ap_name - Using hostname for easy identification
#
# This defines the name used for the AP hotspot, and for the ZeroConf
# host name.
#
ap_name: {hostname}-comitup

# ap_password
#
# If an ap_password is defined, then the AP hotspot is configured with 
# "infrastructure WPA-psk" authentication, requiring this password
# to connect. The password must be between 8 and 63 characters. You
# should reboot after changing this value.
#
# ap_password: supersecretpassword

# primary_wifi_device
#
# By default, the first wifi device returned by NetworkManager is used as
# the primary wifi device. This allows you to override this choice.
# The primary device is used to spawn the access point.
#
primary_wifi_device: wlan0

# Enable GPIO nuke button functionality
# DISABLED to prevent GPIO conflicts with camera controller
# This prevents "Failed to add edge detection" errors
enable_nuke: 0
"""
    
    # Write the dynamic configuration
    with open('/tmp/comitup.conf', 'w') as f:
        f.write(comitup_config)
    run_cmd("sudo mv /tmp/comitup.conf /etc/comitup.conf")
    run_cmd("sudo chown root:root /etc/comitup.conf")
    run_cmd("sudo chmod 644 /etc/comitup.conf")
    
    # Enable the service (don't force start - let it start when needed)
    log_step("COMITUP", "Enabling ComitUp service...")
    run_cmd("sudo systemctl enable comitup")
    
    # Ensure network-online.target works properly for camera services
    log_step("COMITUP", "Configuring network wait services...")
    run_cmd("sudo systemctl enable systemd-networkd-wait-online.service", check=False)
    
    log_step("COMITUP", "ComitUp setup completed - WiFi unblocked and will start when no network is available")
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
        os.chmod(directory, 0o777)
    
    run_cmd("sudo chown -R pi:pi /home/pi/shared")
    
    # Initialize install logging to shared directory now that it exists
    install_logger.set_shared_path("/home/pi/shared")
    log_step("DIRS", "Directory structure created and logging initialized")

def setup_samba():
    """Setup Samba file sharing"""
    log_step("SAMBA", "Setting up Samba file sharing...")
    
    # Install Samba packages only when this feature is enabled.
    if not run_cmd("sudo apt-get install -y --no-install-recommends samba samba-common-bin smbclient avahi-daemon libnss-mdns avahi-utils", check=False):
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
    
    # Install SMB service advertisement for better network discovery
    avahi_smb_source = f"{PROJECT_ROOT}/Services/avahi-smb.service"
    if os.path.exists(avahi_smb_source):
        run_cmd("sudo mkdir -p /etc/avahi/services")
        run_cmd(f"sudo cp {avahi_smb_source} /etc/avahi/services/smb.service")
        log_step("SAMBA", "SMB service advertisement installed")
    else:
        log_step("WARNING", "Avahi SMB service file not found")
    
    # Enable and start Samba services
    run_cmd("sudo systemctl enable smbd nmbd avahi-daemon", check=False)
    run_cmd("sudo systemctl restart smbd nmbd avahi-daemon", check=False)
    run_cmd("sudo systemctl enable wsdd", check=False)
    run_cmd("sudo systemctl restart wsdd", check=False)
    
    # Ensure proper permissions on shared directory for full guest access
    log_step("SAMBA", "Setting permissions for full guest access...")
    run_cmd("sudo chown -R pi:pi /home/pi/shared", check=False)
    run_cmd("sudo find /home/pi/shared -type d -exec chmod 777 {} +", check=False)
    run_cmd("sudo find /home/pi/shared -type f -exec chmod 666 {} +", check=False)
    
    return True

def setup_ds18b20_hardware():
    """Configure DS18B20 1-wire temperature sensor hardware support"""
    log_step("DS18B20", "Configuring DS18B20 temperature sensor hardware...")
    
    # Determine config file path (Bookworm vs older versions)
    config_paths = ["/boot/firmware/config.txt", "/boot/config.txt"]
    config_path = None
    
    for path in config_paths:
        if os.path.exists(path):
            config_path = path
            break
    
    if not config_path:
        log_step("WARNING", "Boot config file not found - DS18B20 configuration skipped")
        return False
    
    log_step("DS18B20", f"Using config file: {config_path}")
    
    # Check if DS18B20 overlay is already configured
    existing_w1_config = run_cmd(f"grep -i 'dtoverlay=w1-gpio' {config_path} || true", capture=True, check=False)
    
    if existing_w1_config:
        log_step("DS18B20", "1-wire overlay already configured")
    else:
        log_step("DS18B20", "Adding 1-wire overlay to boot configuration...")
        # Add DS18B20 configuration to boot config
        overlay_config = "\\n# DS18B20 Temperature Sensor (GPIO 22)\\ndtoverlay=w1-gpio,gpiopin=22\\n"
        run_cmd(f"echo '{overlay_config}' | sudo tee -a {config_path} >/dev/null")
        log_step("DS18B20", "1-wire overlay added to boot configuration")
    
    # Configure required kernel modules
    modules_file = "/etc/modules"
    required_modules = ["w1-gpio", "w1-therm"]
    
    log_step("DS18B20", "Configuring kernel modules...")
    
    for module in required_modules:
        # Check if module is already configured
        existing_module = run_cmd(f"grep -E '^{module}\\\\s*$' {modules_file} || true", capture=True, check=False)
        
        if existing_module:
            log_step("DS18B20", f"Module {module} already configured")
        else:
            log_step("DS18B20", f"Adding {module} to {modules_file}")
            run_cmd(f"echo '{module}' | sudo tee -a {modules_file} >/dev/null")
    
    log_step("DS18B20", "DS18B20 hardware configuration complete")
    log_step("DS18B20", "Note: Reboot required to activate 1-wire interface")
    
    return True

def setup_services():
    """Setup all systemd services"""
    log_step("SERVICES", "Setting up system services...")

    self_heal_script = f"{PROJECT_ROOT}/Services/self_heal_shared.sh"
    if os.path.exists(self_heal_script):
        run_cmd(f"sudo chmod +x {self_heal_script}", check=False)
    else:
        log_step("WARNING", f"Self-heal script not found: {self_heal_script}")
    
    services = [
        ("camcontroller.service", "Services/camcontroller.service"),
        ("camcontroller-web.service", "Services/camcontroller-web.service"),
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
    
    # Restart web service to apply new configuration
    run_cmd("sudo systemctl restart camcontroller-web.service", check=False)

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
    
    # Initialize logging before anything else
    install_logger.log("INFO", "INSTALL", "Starting PyRpiCamController installation")
    
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
    install_logger.log("INFO", "SYSTEM", f"Pi Model: {model_info['full_name']}")
    install_logger.log("INFO", "SYSTEM", f"Memory: {model_info['memory_gb']}GB")
    install_logger.log("INFO", "SYSTEM", f"Serial: {get_serial()}")
    print(f"Pi Model: {model_info['full_name']}")
    print(f"Memory: {model_info['memory_gb']}GB")
    print(f"Serial: {get_serial()}")
    print("=" * 60)
    
    try:
        # Pre-flight checks
        log_step("CHECK", "Verifying project deployment...")
        
        if not os.path.exists(PROJECT_ROOT):
            error_msg = f"Project not found at {PROJECT_ROOT}"
            install_logger.log("ERROR", "CHECK", error_msg)
            print(f"ERROR: {error_msg}")
            print("Please deploy the project first:")
            print(f"git clone https://github.com/teddycool/PyRpiCamController.git {PROJECT_ROOT}")
            sys.exit(1)
        
        required_dirs = ["CamController", "Settings", "WebGui", "Services"]
        for dir_name in required_dirs:
            if not os.path.exists(f"{PROJECT_ROOT}/{dir_name}"):
                error_msg = f"Required directory missing: {dir_name}"
                install_logger.log("ERROR", "CHECK", error_msg)
                print(f"ERROR: {error_msg}")
                sys.exit(1)
        
        log_step("CHECK", "Project deployment verified ✓")
        
        # Package installation
        if not package_install(with_opencv=args.with_opencv):
            log_step("ERROR", "Package installation failed!", "ERROR")
            sys.exit(1)
        
        # ComitUp setup (WiFi management)
        setup_comitup()
        
        # Directory structure
        setup_directories()
        
        # Samba setup
        setup_samba()
        
        # DS18B20 temperature sensor hardware setup
        setup_ds18b20_hardware()
        
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
        
        # Finalize installation logging
        install_logger.finalize(success=True, duration=install_duration)
        
        print("\\n" + "=" * 60)
        print("INSTALLATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Total time: {install_duration} seconds ({install_duration//60}m {install_duration%60}s)")
        print(f"Hostname: {hostname}.local")
        print(f"Web interface: http://{hostname}.local")
        print(f"Samba share: \\\\{hostname}.local\\shared")
        print(f"ComitUp portal: http://10.41.0.1 (when connected to {hostname}-comitup WiFi)")
        print(f"Install log: /home/pi/shared/logs/install_{install_logger.start_time.strftime('%Y%m%d_%H%M%S')}.log")
        print("\\nHardware Configuration:")
        print("• DS18B20 temperature sensor: 1-wire interface configured (GPIO 22)")
        print("• Temperature monitoring: Available in web interface after reboot")
        print("\\nNext steps:")
        print("1. Reboot to activate all services and hardware interfaces")
        print(f"2. Configure WiFi via ComitUp portal (connect to {hostname}-comitup network)")
        print("3. Access web interface for camera and temperature monitoring")
        print("4. Connect DS18B20 temperature sensor to GPIO 22 if desired")
        print("=" * 60)
            
    except KeyboardInterrupt:
        end_time = time.time()
        install_duration = int(end_time - start_time)
        log_step("INTERRUPT", "Installation interrupted by user", "WARNING")
        install_logger.finalize(success=False, duration=install_duration)
        sys.exit(0)
    except Exception as e:
        end_time = time.time()
        install_duration = int(end_time - start_time)
        log_step("ERROR", f"Installation failed: {e}", "ERROR")
        install_logger.finalize(success=False, duration=install_duration)
        sys.exit(1)

if __name__ == "__main__":
    main()