#!/usr/bin/env python3
"""
Test script for camera controller service only
Configures and starts just the camcontroller.service
"""

import os
import subprocess
import sys
import time

def log(message):
    print(f"[CAM-TEST] {message}")

def run_cmd(cmd, check=True):
    """Run command and return success/failure"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def setup_camera_service():
    """Setup and test camera controller service only"""
    
    PROJECT_ROOT = "/home/pi/PyRpiCamController"
    
    log("=== Camera Controller Service Test ===")
    
    # Check if project exists
    if not os.path.exists(PROJECT_ROOT):
        log(f"ERROR: Project not found at {PROJECT_ROOT}")
        return False
    
    # Check if camera service file exists
    service_file = f"{PROJECT_ROOT}/Services/camcontroller.service"
    if not os.path.exists(service_file):
        log(f"ERROR: Service file not found: {service_file}")
        return False
    
    # Stop any running camera service
    log("Stopping any existing camera service...")
    run_cmd("sudo systemctl stop camcontroller", check=False)
    
    # Copy service file
    log("Installing camera service file...")
    success, stdout, stderr = run_cmd(f"sudo cp {service_file} /etc/systemd/system/camcontroller.service")
    if not success:
        log(f"ERROR: Failed to copy service file: {stderr}")
        return False
    
    # Reload systemd
    log("Reloading systemd...")
    success, _, stderr = run_cmd("sudo systemctl daemon-reload")
    if not success:
        log(f"ERROR: Failed to reload systemd: {stderr}")
        return False
    
    # Create basic directories
    log("Creating basic directories...")
    run_cmd("sudo mkdir -p /home/pi/shared/images", check=False)
    run_cmd("sudo mkdir -p /home/pi/shared/logs", check=False)
    run_cmd("sudo chown -R pi:pi /home/pi/shared", check=False)
    
    # Start camera service
    log("Starting camera service...")
    success, stdout, stderr = run_cmd("sudo systemctl start camcontroller")
    if not success:
        log(f"ERROR: Failed to start camera service: {stderr}")
        return False
    
    # Wait a moment for startup
    time.sleep(3)
    
    # Check service status
    log("Checking camera service status...")
    success, stdout, stderr = run_cmd("sudo systemctl is-active camcontroller")
    if success and "active" in stdout:
        log("✓ Camera service is running!")
        
        # Show recent logs
        log("Recent camera service logs:")
        success, stdout, stderr = run_cmd("sudo journalctl -u camcontroller --no-pager -n 10")
        if success:
            for line in stdout.split('\n')[-10:]:
                if line.strip():
                    print(f"   {line}")
        
        return True
    else:
        log(f"✗ Camera service failed to start: {stderr}")
        
        # Show error logs
        log("Error logs:")
        success, stdout, stderr = run_cmd("sudo journalctl -u camcontroller --no-pager -n 20")
        if success:
            for line in stdout.split('\n')[-20:]:
                if line.strip():
                    print(f"   {line}")
        
        return False

def stop_camera_service():
    """Stop camera service"""
    log("Stopping camera service...")
    run_cmd("sudo systemctl stop camcontroller", check=False)
    run_cmd("sudo systemctl disable camcontroller", check=False)

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "stop":
            stop_camera_service()
        else:
            success = setup_camera_service()
            if not success:
                log("Camera service test FAILED")
                sys.exit(1)
            else:
                log("Camera service test PASSED")
                log("Use 'python3 test_camera_service.py stop' to stop the service")
    except KeyboardInterrupt:
        log("Interrupted by user")
        stop_camera_service()