#!/usr/bin/env python3
"""
Test script for web service only
Configures and starts just the camcontroller-web.service
"""

import os
import subprocess
import sys
import time
import requests

def log(message):
    print(f"[WEB-TEST] {message}")

def run_cmd(cmd, check=True):
    """Run command and return success/failure"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def test_web_access(port=80):
    """Test if web interface is accessible"""
    try:
        response = requests.get(f"http://localhost:{port}", timeout=5)
        return response.status_code == 200
    except:
        return False

def setup_web_service():
    """Setup and test web service only"""
    
    PROJECT_ROOT = "/home/pi/PyRpiCamController"
    
    log("=== Web Service Test ===")
    
    # Check if project exists
    if not os.path.exists(PROJECT_ROOT):
        log(f"ERROR: Project not found at {PROJECT_ROOT}")
        return False
    
    # Check if web service file exists
    service_file = f"{PROJECT_ROOT}/Services/camcontroller-web.service"
    if not os.path.exists(service_file):
        log(f"ERROR: Web service file not found: {service_file}")
        return False
    
    # Check if web app exists
    web_app = f"{PROJECT_ROOT}/WebGui/web_app.py"
    if not os.path.exists(web_app):
        log(f"ERROR: Web app not found: {web_app}")
        return False
    
    # Stop any running web service
    log("Stopping any existing web service...")
    run_cmd("sudo systemctl stop camcontroller-web", check=False)
    
    # Copy service file
    log("Installing web service file...")
    success, stdout, stderr = run_cmd(f"sudo cp {service_file} /etc/systemd/system/camcontroller-web.service")
    if not success:
        log(f"ERROR: Failed to copy service file: {stderr}")
        return False
    
    # Reload systemd
    log("Reloading systemd...")
    success, _, stderr = run_cmd("sudo systemctl daemon-reload")
    if not success:
        log(f"ERROR: Failed to reload systemd: {stderr}")
        return False
    
    # Create settings directory if needed
    log("Ensuring settings directory exists...")
    run_cmd("sudo mkdir -p /home/pi/PyRpiCamController/Settings", check=False)
    run_cmd("sudo chown -R pi:pi /home/pi/PyRpiCamController", check=False)
    
    # Create minimal user_settings.json if it doesn't exist
    user_settings_file = f"{PROJECT_ROOT}/Settings/user_settings.json"
    if not os.path.exists(user_settings_file):
        log("Creating minimal user_settings.json...")
        with open(user_settings_file, 'w') as f:
            f.write('{}\\n')
    
    # Start web service
    log("Starting web service...")
    success, stdout, stderr = run_cmd("sudo systemctl start camcontroller-web")
    if not success:
        log(f"ERROR: Failed to start web service: {stderr}")
        return False
    
    # Wait a moment for startup
    time.sleep(5)
    
    # Check service status
    log("Checking web service status...")
    success, stdout, stderr = run_cmd("sudo systemctl is-active camcontroller-web")
    if success and "active" in stdout:
        log("✓ Web service is running!")
        
        # Test web access
        log("Testing web interface access...")
        if test_web_access(80):
            log("✓ Web interface is accessible at http://localhost")
        else:
            log("✗ Web interface not accessible - check port or firewall")
        
        # Show recent logs
        log("Recent web service logs:")
        success, stdout, stderr = run_cmd("sudo journalctl -u camcontroller-web --no-pager -n 10")
        if success:
            for line in stdout.split('\n')[-10:]:
                if line.strip():
                    print(f"   {line}")
        
        return True
    else:
        log(f"✗ Web service failed to start: {stderr}")
        
        # Show error logs
        log("Error logs:")
        success, stdout, stderr = run_cmd("sudo journalctl -u camcontroller-web --no-pager -n 20")
        if success:
            for line in stdout.split('\n')[-20:]:
                if line.strip():
                    print(f"   {line}")
        
        return False

def stop_web_service():
    """Stop web service"""
    log("Stopping web service...")
    run_cmd("sudo systemctl stop camcontroller-web", check=False)
    run_cmd("sudo systemctl disable camcontroller-web", check=False)

def test_direct_run():
    """Test running web app directly (not as service)"""
    PROJECT_ROOT = "/home/pi/PyRpiCamController"
    web_app = f"{PROJECT_ROOT}/WebGui/web_app.py"
    
    log("=== Direct Web App Test ===")
    log("Testing web app directly (not as service)...")
    log(f"Running: python3 {web_app}")
    log("This will run in foreground - use Ctrl+C to stop")
    
    try:
        # Change to correct directory
        os.chdir(f"{PROJECT_ROOT}/WebGui")
        # Run web app directly
        subprocess.run([sys.executable, "web_app.py"], check=True)
    except KeyboardInterrupt:
        log("Direct web app test stopped by user")
    except Exception as e:
        log(f"Direct web app test failed: {e}")

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "stop":
                stop_web_service()
            elif sys.argv[1] == "direct":
                test_direct_run()
            else:
                log("Usage: python3 test_web_service.py [stop|direct]")
        else:
            success = setup_web_service()
            if not success:
                log("Web service test FAILED")
                log("Try 'python3 test_web_service.py direct' to test without systemd")
                sys.exit(1)
            else:
                log("Web service test PASSED")
                log("Use 'python3 test_web_service.py stop' to stop the service")
                log("Use 'python3 test_web_service.py direct' to run directly")
    except KeyboardInterrupt:
        log("Interrupted by user")
        stop_web_service()