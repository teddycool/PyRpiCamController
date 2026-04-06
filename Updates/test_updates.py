#!/usr/bin/env python3
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

"""
OTA System Test Script

This script validates the OTA system configuration and components.
Run this before deploying OTA to ensure everything is properly configured.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from Settings.settings_manager import settings_manager
        print("✓ settings_manager import OK")
    except ImportError as e:
        print(f"✗ settings_manager import failed: {e}")
        return False
    
    try:
        import requests
        print("✓ requests import OK")
    except ImportError as e:
        print(f"✗ requests import failed: {e}")
        print("  Install with: pip install requests")
        return False
    
    return True

def test_directories():
    """Test that required directories exist."""
    print("\nTesting directories...")
    
    required_dirs = [
        '/home/pi/ota',
        '/home/pi/ota/backups',
        '/home/pi/ota/downloads',
        '/home/pi/ota/temp',
        '/home/pi/Updates/backup',
        '/home/pi/Updates/staging'
    ]
    
    success = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path} exists")
        else:
            print(f"✗ {dir_path} missing")
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                print(f"✓ Created {dir_path}")
            except Exception as e:
                print(f"✗ Could not create {dir_path}: {e}")
                success = False
    
    return success

def test_settings():
    """Test OTA settings configuration."""
    print("\nTesting OTA settings...")
    
    try:
        from Settings.settings_manager import settings_manager
        
        # Test basic OTA setting
        ota_enabled = settings_manager.get('OtaEnable', False)
        print(f"✓ OTA Enabled: {ota_enabled}")
        
        # Test OTA configuration
        try:
            server_url = settings_manager.get('OTA.server_url', 'not configured')
            print(f"✓ Server URL: {server_url}")
            
            check_interval = settings_manager.get('OTA.check_interval', 3600)
            print(f"✓ Check interval: {check_interval}s")
            
            api_key = settings_manager.get('OTA.api_key', '')
            if api_key:
                print("✓ API key configured")
            else:
                print("! API key not configured (optional for testing)")
                
        except Exception as e:
            print(f"✗ Error reading OTA settings: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Error accessing settings: {e}")
        return False
    
    return True

def test_ota_manager():
    """Test OTA manager instantiation."""
    print("\nTesting OTA manager...")
    
    try:
        sys.path.append('/home/pi/PyRpiCamController/ota/install')
        from installota_v2 import OTAManager
        
        ota = OTAManager()
        print("✓ OTA manager created successfully")
        
        # Test CPU serial
        cpu_serial = ota.get_cpu_serial()
        print(f"✓ CPU serial: {cpu_serial}")
        
        # Test configuration
        if ota.config:
            print("✓ OTA configuration loaded")
        else:
            print("✗ OTA configuration failed")
            return False
            
    except Exception as e:
        print(f"✗ Error creating OTA manager: {e}")
        return False
    
    return True

def test_permissions():
    """Test file permissions."""
    print("\nTesting permissions...")
    
    # Check if recovery script is executable
    recovery_script = Path('/home/pi/PyRpiCamController/ota/recovery.sh')
    if recovery_script.exists():
        if os.access(recovery_script, os.X_OK):
            print("✓ Recovery script is executable")
        else:
            print("✗ Recovery script is not executable")
            print("  Run: chmod +x ota/recovery.sh")
            return False
    else:
        print("✗ Recovery script not found")
        return False
    
    return True

def test_service_commands():
    """Test systemd service commands (requires systemd)."""
    print("\nTesting service commands...")
    
    # Test if we can check service status (don't actually start/stop)
    try:
        result = subprocess.run(['systemctl', 'is-enabled', 'camcontroller.service'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ camcontroller.service is enabled")
        else:
            print("! camcontroller.service is not enabled (normal for development)")
            
        # Check if ota-daemon service file exists
        service_file = Path('/etc/systemd/system/camcontroller-update.service')
        if service_file.exists():
            print("✓ camcontroller-update.service file exists")
        else:
            print("! camcontroller-update.service not installed")
            print("  Install with: sudo cp Services/camcontroller-update.service /etc/systemd/system/")
            
    except Exception as e:
        print(f"! Could not test services (normal in containers): {e}")
    
    return True

def test_version_file():
    """Test version file handling."""
    print("\nTesting version file...")
    
    project_root = Path('/home/pi/PyRpiCamController')
    version_file = project_root / 'VERSION'
    
    if version_file.exists():
        version = version_file.read_text().strip()
        print(f"✓ VERSION file exists: {version}")
    else:
        print("! VERSION file missing")
        try:
            version_file.write_text('1.0.0-dev\n')
            print("✓ Created VERSION file with '1.0.0-dev'")
        except Exception as e:
            print(f"✗ Could not create VERSION file: {e}")
            return False
    
    return True

def run_all_tests():
    """Run all tests and return overall result."""
    print("=== OTA System Validation ===\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Directory Tests", test_directories),
        ("Settings Tests", test_settings),
        ("OTA Manager Tests", test_ota_manager),
        ("Permission Tests", test_permissions),
        ("Service Tests", test_service_commands),
        ("Version File Tests", test_version_file)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! OTA system is ready.")
        return True
    else:
        print(f"\n⚠️  {len(tests) - passed} tests failed. Fix issues before deploying OTA.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)