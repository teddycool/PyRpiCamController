#!/usr/bin/env python3
"""
Test script to validate Pi OTA registration components locally
This helps test the registration process before deploying to actual Pi hardware
"""

import json
import requests
import sys
import os
from pathlib import Path

def test_registration_components():
    """Test the OTA registration process components"""
    print("🧪 Testing OTA Registration Components")
    print("="*50)
    
    project_root = Path(__file__).parent.parent
    
    # Test 1: Check file structure
    print(f"\n1️⃣ Checking file structure...")
    setup_script = project_root / "tools" / "setup_ota_registration.py"
    credentials_file = project_root / "tools" / "ota_credentials.txt"
    
    print(f"   Setup script: {'✅ Found' if setup_script.exists() else '❌ Missing'}")
    print(f"   Credentials file: {'✅ Found' if credentials_file.exists() else '❌ Missing'}")
    
    if not setup_script.exists():
        print("❌ Setup script missing - cannot continue")
        return False
    
    # Test 2: Check OTA server connectivity  
    print(f"\n2️⃣ Testing OTA server connectivity...")
    OTA_SERVER_URL = "https://www.sensorwebben.se/pycamota"
    
    try:
        response = requests.get(f"{OTA_SERVER_URL}/admin/admin_dashboard.php", timeout=10)
        if response.status_code == 200:
            print("✅ OTA server is reachable")
        else:
            print(f"⚠️  OTA server responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach OTA server: {e}")
        return False
    
    # Test 3: Try to load setup script components
    print(f"\n3️⃣ Testing setup script components...")
    try:
        sys.path.insert(0, str(project_root / "tools"))
        import setup_ota_registration
        
        setup = setup_ota_registration.OTASetup()
        print("✅ Setup script imports successfully")
        
        # Test credential loading if credentials file exists
        if credentials_file.exists():
            username, password = setup.load_admin_credentials()
            if username and password:
                print(f"✅ Admin credentials loaded: {username}")
            else:
                print("❌ Could not load admin credentials from credentials file")
                return False
        else:
            print("⚠️  No credentials file - will need to be created on Pi")
        
        # Test device info simulation
        setup.cpu_id = "1000000012345678"  # Test CPU ID
        setup.get_device_info()
        print(f"✅ Device info generation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup script test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_deployment_instructions():
    """Show how to deploy this to a Pi"""
    print(f"\n📋 Pi Deployment Instructions")
    print("="*50)
    
    print(f"""
🚀 To register a Pi device with the OTA system:

1️⃣ **Copy files to Pi:**
   scp tools/setup_ota_registration.py pi@your-pi:/home/pi/
   scp tools/ota_credentials.txt pi@your-pi:/home/pi/

2️⃣ **Run registration on Pi:**
   sudo python3 setup_ota_registration.py

3️⃣ **Credentials are automatically cleaned up after registration**

🔧 **What the script does:**
   ✅ Gets Pi's CPU serial number
   ✅ Registers device with OTA server  
   ✅ Stores API key in device settings
   ✅ Tests the registration
   ✅ Cleans up admin credentials
   ✅ Leaves only the API key for future updates

🔐 **Security:**
   - Admin credentials are removed from Pi after registration
   - Only the device-specific API key remains
   - API key is stored in settings (encrypted)
""")

def main():
    print("🔧 PyRpiCamController OTA Registration Validator")
    print("This validates the Pi registration process components\n")
    
    success = test_registration_components()
    
    if success:
        print(f"\n✅ All components working! Ready for Pi deployment")
        show_deployment_instructions()
    else:
        print(f"\n❌ Component test failed - fix issues before Pi deployment")
        print(f"\n💡 Common issues:")
        print(f"   - Missing secrets.php file")
        print(f"   - Network connectivity to OTA server")
        print(f"   - Incorrect admin credentials in secrets")
        
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()