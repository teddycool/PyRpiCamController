#!/usr/bin/env python3
"""
SMB (Samba) Service Test Script for PyRpiCamController
Tests SMB file sharing functionality
"""

import os
import sys
import subprocess
import time
import socket
from datetime import datetime

# Configuration
PROJECT_ROOT = "/home/pi/PyRpiCamController"
SHARED_DIR = "/home/pi/shared"
SMB_CONF_SOURCE = f"{PROJECT_ROOT}/Services/smb.conf"
SMB_CONF_TARGET = "/etc/samba/smb.conf"
SMB_CREDENTIALS_ENV = f"{SHARED_DIR}/smb_credentials.env"

def log(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[SMB-TEST] {message}")
    
    # Also log to file if possible
    log_file = f"{SHARED_DIR}/logs/smb_test.log"
    if os.path.exists(os.path.dirname(log_file)):
        try:
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass

def run_cmd(command, check=True):
    """Run a command and return success status"""
    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True)
        
        if check and result.returncode != 0:
            log(f"Command failed: {command}")
            if result.stderr:
                log(f"Error: {result.stderr.strip()}")
            return False, result.stdout, result.stderr
        
        return True, result.stdout, result.stderr
    except Exception as e:
        if check:
            log(f"Exception running command: {e}")
        return False, "", str(e)

def command_exists(command):
    """Check if a command exists"""
    success, _, _ = run_cmd(f"command -v {command}", check=False)
    return success

def service_is_active(service_name):
    """Check if a systemd service is active"""
    success, _, _ = run_cmd(f"systemctl is-active {service_name}", check=False)
    return success

def load_smb_credentials():
    """Load installer-generated SMB credentials for authenticated Mode B testing."""
    if not os.path.exists(SMB_CREDENTIALS_ENV):
        return None

    creds = {}
    try:
        with open(SMB_CREDENTIALS_ENV, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                creds[key.strip()] = value.strip()
    except Exception as e:
        log(f"⚠ Failed to read SMB credentials file: {e}")
        return None

    username = creds.get("SMB_USERNAME")
    password = creds.get("SMB_PASSWORD")
    if not username or not password:
        return None

    return {
        "username": username,
        "password": password,
        "hostname": creds.get("SMB_HOSTNAME", socket.gethostname()),
        "share": creds.get("SMB_SHARE", "shared"),
    }

def stop_smb_services():
    """Stop SMB services"""
    log("Stopping SMB services...")
    run_cmd("sudo systemctl stop smbd", check=False)
    run_cmd("sudo systemctl stop nmbd", check=False)
    log("SMB services stopped.")

def test_smb_service():
    """Main SMB service test function"""
    log("=== SMB (Samba) Service Test ===")
    log("Testing SMB file sharing functionality for PyRpiCamController")
    log(f"Date: {datetime.now()}")
    log(f"Hostname: {socket.gethostname()}")
    
    try:
        # Get the actual network IP address, not localhost
        import subprocess
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0:
            ip_address = result.stdout.strip().split()[0]  # Get first IP
            log(f"IP Address: {ip_address}")
        else:
            # Fallback to socket method
            ip_address = socket.gethostbyname(socket.gethostname())
            log(f"IP Address: {ip_address}")
    except:
        ip_address = "127.0.0.1"
        log("IP Address: Unable to determine")
    
    print()
    
    # Check if project exists
    if not os.path.exists(PROJECT_ROOT):
        log(f"✗ ERROR: Project not found at {PROJECT_ROOT}")
        return False
    
    # Check if SMB config file exists
    if not os.path.exists(SMB_CONF_SOURCE):
        log(f"✗ ERROR: SMB config file not found: {SMB_CONF_SOURCE}")
        return False
    
    # Check sudo access
    success, _, _ = run_cmd("sudo -n true", check=False)
    if not success:
        log("✗ ERROR: This script requires sudo access to configure SMB services")
        return False
    
    smb_credentials = load_smb_credentials()
    auth_mode = smb_credentials is not None

    # Install Samba if not present
    log("Checking if Samba is installed...")
    if not command_exists('smbd') and not command_exists('samba'):
        log("Installing Samba...")
        success, _, stderr = run_cmd("sudo apt-get update && sudo apt-get install -y samba samba-common-bin")
        if not success:
            log(f"✗ Failed to install Samba: {stderr}")
            return False
        log("✓ Samba installed successfully")
    else:
        log("✓ Samba is already installed")
    
    # Create shared directory structure
    log("Creating shared directory structure...")
    success, _, stderr = run_cmd(f"sudo mkdir -p '{SHARED_DIR}/logs'")
    if not success:
        log(f"✗ Failed to create shared directory: {stderr}")
        return False
    
    # Set proper permissions
    log("Setting directory permissions...")
    success, _, stderr = run_cmd(f"sudo chown -R pi:pi '{SHARED_DIR}'")
    if not success:
        log(f"✗ Failed to set ownership: {stderr}")
        return False
    
    success, _, stderr = run_cmd(f"sudo chmod -R 755 '{SHARED_DIR}'")
    if not success:
        log(f"✗ Failed to set permissions: {stderr}")
        return False
    
    log("✓ Shared directory created and configured")
    
    # Backup existing SMB configuration
    if os.path.exists(SMB_CONF_TARGET):
        log("Backing up existing SMB configuration...")
        backup_name = f"{SMB_CONF_TARGET}.backup.{int(time.time())}"
        success, _, stderr = run_cmd(f"sudo cp '{SMB_CONF_TARGET}' '{backup_name}'")
        if success:
            log("✓ Existing SMB configuration backed up")
        else:
            log("⚠ Failed to backup existing SMB configuration")
    
    if auth_mode:
        log("Authenticated SMB mode detected - keeping existing installer-generated smb.conf")
    else:
        # Install new SMB configuration (legacy guest fallback)
        log("Installing SMB configuration...")
        success, _, stderr = run_cmd(f"sudo cp '{SMB_CONF_SOURCE}' '{SMB_CONF_TARGET}'")
        if not success:
            log(f"✗ Failed to install SMB configuration: {stderr}")
            return False
        log("✓ SMB configuration installed")
    
    # Set shared directory permissions
    log("Setting directory permissions...")
    success, _, stderr = run_cmd(f"sudo chmod 755 /home/pi")
    if not success:
        log(f"⚠ Failed to set /home/pi permissions: {stderr}")
    
    target_mode = "775" if auth_mode else "777"
    success, _, stderr = run_cmd(f"sudo chmod {target_mode} '{SHARED_DIR}'")
    if not success:
        log(f"⚠ Failed to set shared directory permissions: {stderr}")
    
    if auth_mode:
        run_cmd(f"sudo find '{SHARED_DIR}' -type d -exec chmod 775 {{}} +", check=False)
        run_cmd(f"sudo find '{SHARED_DIR}' -type f -exec chmod 664 {{}} +", check=False)
    else:
        success, _, stderr = run_cmd(f"sudo chmod -R 666 '{SHARED_DIR}'/*")
        run_cmd(f"find '{SHARED_DIR}' -type d -exec sudo chmod 777 {{}} \;", check=False)
    
    log("✓ Directory permissions configured")
    
    # Test SMB configuration
    log("Testing SMB configuration...")
    if command_exists('testparm'):
        success, stdout, stderr = run_cmd(f"sudo testparm -s '{SMB_CONF_TARGET}'", check=False)
        if success:
            log("✓ SMB configuration is valid")
        else:
            log("⚠ SMB configuration has warnings (but may still work)")
    else:
        log("⚠ testparm not available, skipping configuration validation")
    
    # Stop existing services
    log("Stopping existing SMB services...")
    run_cmd("sudo systemctl stop smbd", check=False)
    run_cmd("sudo systemctl stop nmbd", check=False)
    
    # Start SMB services
    log("Starting SMB services...")
    success, _, stderr = run_cmd("sudo systemctl start smbd")
    if not success:
        log(f"✗ Failed to start smbd service: {stderr}")
        return False
    
    success, _, stderr = run_cmd("sudo systemctl start nmbd")
    if not success:
        log(f"✗ Failed to start nmbd service: {stderr}")
        return False
    
    log("✓ SMB services started")
    
    # Enable services for startup
    log("Enabling SMB services for auto-start...")
    run_cmd("sudo systemctl enable smbd", check=False)
    run_cmd("sudo systemctl enable nmbd", check=False)
    log("✓ SMB services enabled for auto-start")
    
    # Check service status
    log("Checking service status...")
    
    if service_is_active("smbd"):
        log("✓ smbd service is running")
    else:
        log("✗ smbd service is not running")
        run_cmd("sudo systemctl status smbd", check=False)
        return False
    
    if service_is_active("nmbd"):
        log("✓ nmbd service is running")
    else:
        log("⚠ nmbd service is not running (NetBIOS name service)")
        run_cmd("sudo systemctl status nmbd", check=False)
    
    # Check wsdd service for Windows discovery
    if service_is_active("wsdd"):
        log("✓ wsdd service is running (Windows Service Discovery)")
    else:
        log("⚠ wsdd service is not running (Windows discovery may not work)")
        run_cmd("sudo systemctl status wsdd", check=False)
    
    # Test file operations
    log("Testing file operations...")
    
    # Create a test file
    test_file = f"{SHARED_DIR}/smb_test_{int(time.time())}.txt"
    test_content = f"SMB Test File Created: {datetime.now()}"
    
    try:
        with open(test_file, 'w') as f:
            f.write(test_content)
        log(f"✓ Created test file: {os.path.basename(test_file)}")
        
        # Verify file exists and is readable
        if os.path.exists(test_file) and os.access(test_file, os.R_OK):
            log("✓ Test file is accessible")
            
            # Clean up test file
            os.remove(test_file)
            log("✓ Test file cleaned up")
        else:
            log("✗ Test file is not accessible")
    except Exception as e:
        log(f"✗ Failed to create test file: {e}")
    
    # Network connectivity test
    log("Testing network accessibility...")
    hostname = socket.gethostname()
    
    # Test NetBIOS name resolution
    log(f"Checking NetBIOS name resolution for {hostname}...")
    success, stdout, _ = run_cmd(f"nmblookup {hostname}", check=False)
    if success:
        log(f"✓ NetBIOS name {hostname} resolves correctly")
    else:
        log(f"⚠ NetBIOS name {hostname} resolution failed")
    
    # Test avahi service advertising
    log("Checking SMB service advertising...")
    if command_exists('avahi-browse'):
        success, stdout, _ = run_cmd("timeout 5 avahi-browse -t _smb._tcp --terminate", check=False)
        if success and "smb" in stdout.lower():
            log("✓ SMB services are being advertised via mDNS")
        else:
            log("⚠ SMB service advertising may not be working")
    else:
        log("⚠ avahi-browse not available - install with: sudo apt-get install avahi-utils")
    
    if command_exists('smbclient'):
        log("Testing SMB share accessibility...")

        if auth_mode:
            username = smb_credentials["username"]
            password = smb_credentials["password"]
            share_name = smb_credentials.get("share", "shared")
            auth_list_cmd_ip = f"timeout 10 smbclient -L //{ip_address} -U '{username}%{password}'"
            auth_share_cmd_ip = f"timeout 10 smbclient //{ip_address}/{share_name} -U '{username}%{password}' -c 'ls; quit'"
            auth_list_cmd_host = f"timeout 10 smbclient -L //{hostname} -U '{username}%{password}'"
            log(f"Using authenticated SMB test user: {username}")
        else:
            auth_list_cmd_ip = f"timeout 10 smbclient -L //{ip_address} -U% -N"
            auth_share_cmd_ip = f"timeout 10 smbclient //{ip_address}/shared -U% -c 'ls; quit'"
            auth_list_cmd_host = f"timeout 10 smbclient -L //{hostname} -U% -N"
        
        success, _, _ = run_cmd(auth_list_cmd_ip, check=False)
        if success:
            log("✓ SMB shares are accessible")
            
            # Test specific share access
            success, _, _ = run_cmd(auth_share_cmd_ip, check=False)
            if success:
                log("✓ shared is accessible")
            else:
                log("⚠ shared access test failed")
        else:
            log("⚠ SMB share listing failed (but shares may still work)")
            
        # Also test with hostname
        log(f"Testing access with hostname {hostname}...")
        success, _, _ = run_cmd(auth_list_cmd_host, check=False)
        if success:
            log(f"✓ SMB accessible via hostname {hostname}")
        else:
            log(f"⚠ SMB access via hostname {hostname} failed")
    else:
        log("⚠ smbclient not available, skipping network accessibility test")
        log("You can install it with: sudo apt-get install smbclient")
    
    # Firewall check
    log("Checking firewall status...")
    if command_exists('ufw'):
        success, stdout, _ = run_cmd("sudo ufw status", check=False)
        if success and "Status: active" in stdout:
            log("⚠ UFW firewall is active - ensure SMB ports are open")
            log("Run: sudo ufw allow 445/tcp && sudo ufw allow 139/tcp && sudo ufw allow 137:138/udp")
        else:
            log("✓ UFW firewall is inactive or not configured")
    
    # Display summary
    print()
    log("=== SMB Test Summary ===")
    log("✓ SMB services are configured and running")
    log("Share name: shared")
    log(f"Share path: {SHARED_DIR}")
    log("Network access:")
    log(f"  • SMB: smb://{hostname}.local/shared")
    log(f"  • IP:  smb://{ip_address}/shared")
    if auth_mode:
        log(f"  • Authentication required: {smb_credentials['username']}")
    else:
        log("  • Guest access enabled (mapped to 'pi' account)")
    
    print()
    log(f"Access from Windows: \\\\{hostname}\\shared or \\\\{ip_address}\\shared")
    log(f"Access from macOS: smb://{hostname}.local/shared")
    log("Access from Linux: smb://{ip_address}/shared or smb://{hostname}.local/shared")
    
    # Service logs check
    print()
    log("Recent service logs:")
    log("SMB daemon logs:")
    run_cmd("sudo journalctl -u smbd --since '5 minutes ago' --no-pager -n 5", check=False)
    
    print()
    log("Use 'python3 test_smb_service.py stop' to stop the SMB services")
    log("✓ SMB service test completed successfully!")
    
    return True

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == 'stop':
        stop_smb_services()
        return
    
    try:
        if test_smb_service():
            sys.exit(0)
        else:
            log("✗ SMB service test FAILED")
            sys.exit(1)
    except KeyboardInterrupt:
        log("Test interrupted by user")
        stop_smb_services()
        sys.exit(1)
    except Exception as e:
        log(f"✗ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()