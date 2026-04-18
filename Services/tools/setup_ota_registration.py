#!/usr/bin/env python3
"""
OTA Setup and Registration Script for PyRpiCamController

This script should be run ONCE on each Pi during initial setup.
It will:
1. Register the device with the OTA server using admin credentials
2. Store the API key in device settings
3. Test the registration
4. Clean up admin credentials from the device
5. Verify the update system works

Requirements:
- Must be run with admin privileges (sudo)
- Requires internet connection
- Needs backend/Updates/utils/secrets.php with admin credentials
"""

import json
import requests
import sys
import os
import subprocess
import hashlib
from pathlib import Path
import tempfile
import shutil

# OTA Server Configuration
OTA_SERVER_URL = "https://www.sensorwebben.se/pycamota"
DEVICE_API_ENDPOINT = f"{OTA_SERVER_URL}/api/device_management.php"
UPDATE_API_ENDPOINT = f"{OTA_SERVER_URL}/api/update_check.php"

class OTASetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.credentials_file = Path(__file__).parent / "ota_credentials.txt"  # Simple credentials file
        self.settings_manager_path = self.project_root / "Settings" / "settings_manager.py"
        self.cpu_id = None
        self.device_info = {}
        
    def get_cpu_id(self):
        """Get the Raspberry Pi CPU serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'Serial' in line:
                        serial = line.split(':')[1].strip()
                        # Clean and format the serial
                        clean_serial = serial.lower().replace('0x', '').zfill(16)
                        self.cpu_id = clean_serial
                        return clean_serial
            
            print("❌ Could not find CPU serial in /proc/cpuinfo")
            return None
        except Exception as e:
            print(f"❌ Error reading CPU info: {e}")
            return None
    
    def get_device_info(self):
        """Gather device information for registration"""
        try:
            # Get hostname
            hostname = subprocess.check_output(['hostname'], encoding='utf-8').strip()
            
            # Get model info
            try:
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read().strip().replace('\x00', '')
            except:
                model = "Unknown Pi Model"
            
            # Try to get location from hostname or use default
            if 'kitchen' in hostname.lower():
                location = "Kitchen"
            elif 'living' in hostname.lower():
                location = "Living Room"
            elif 'bedroom' in hostname.lower():
                location = "Bedroom"
            elif 'office' in hostname.lower():
                location = "Office"
            else:
                location = "Unknown"
            
            self.device_info = {
                'device_name': f"CamController-{hostname}",
                'location': location,
                'model': model,
                'hostname': hostname
            }
            
            print(f"📱 Device Info:")
            print(f"   CPU ID: {self.cpu_id}")
            print(f"   Name: {self.device_info['device_name']}")
            print(f"   Location: {self.device_info['location']}")
            print(f"   Model: {self.device_info['model']}")
            
        except Exception as e:
            print(f"❌ Error gathering device info: {e}")
            self.device_info = {
                'device_name': f"CamController-{self.cpu_id[:8]}",
                'location': "Unknown"
            }
    
    def load_admin_credentials(self):
        """Load admin credentials from simple credentials file"""
        if not self.credentials_file.exists():
            print(f"❌ Credentials file not found: {self.credentials_file}")
            print("   Create ota_credentials.txt with ADMIN_USERNAME and ADMIN_PASSWORD")
            return None, None
        
        try:
            username = None
            password = None
            
            with open(self.credentials_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('ADMIN_USERNAME='):
                        username = line.split('=', 1)[1]
                    elif line.startswith('ADMIN_PASSWORD='):
                        password = line.split('=', 1)[1]
            
            if username and password:
                print("✅ Admin credentials loaded from credentials file")
                return username, password
            else:
                print("❌ Could not find admin credentials in credentials file")
                print("   Expected: ADMIN_USERNAME=... and ADMIN_PASSWORD=...")
                return None, None
                
        except Exception as e:
            print(f"❌ Error reading credentials file: {e}")
            return None, None
    
    def register_device(self, username, password):
        """Register this device with the OTA server using HTTP Basic Auth"""
        print(f"\n🔐 Registering device with OTA server...")
        
        try:
            # Try multiple authentication methods
            
            # Method 1: Try HTTP Basic Auth first
            import base64
            auth_header = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/json'
            }
            
            registration_data = {
                "action": "register",
                "cpu_id": self.cpu_id,
                "device_name": self.device_info['device_name'],
                "location": self.device_info['location'],
                "update_group": "production"
            }
            
            print("🔐 Attempting registration with Basic Auth...")
            response = requests.post(
                DEVICE_API_ENDPOINT,
                json=registration_data,
                headers=headers,
                timeout=15
            )
            
            print(f"Basic Auth response: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                api_key = data['api_key']
                print(f"✅ Device registered successfully!")
                print(f"🔑 API Key: {api_key[:16]}...")
                return api_key
            elif response.status_code == 409:
                print("⚠️  Device already registered")
                try:
                    data = response.json()
                    if 'api_key' in data:
                        print(f"🔑 Using existing API Key: {data['api_key'][:16]}...")
                        return data['api_key']
                except:
                    pass
                return None
            
            # Method 2: If Basic Auth fails, try session-based auth
            print("🔐 Basic Auth failed, trying session-based auth...")
            
            session = requests.Session()
            
            # Get login page for CSRF token
            login_page = session.get(f"{OTA_SERVER_URL}/admin/admin_login.php", timeout=10)
            csrf_token = None
            
            # Extract CSRF token from the login page
            import re
            csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                print(f"Found CSRF token: {csrf_token[:16]}...")
            else:
                print("⚠️  No CSRF token found, trying without...")
            
            # Submit login form
            login_data = {
                'username': username,
                'password': password,
            }
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            login_response = session.post(
                f"{OTA_SERVER_URL}/admin/admin_login.php",
                data=login_data,
                timeout=10,
                allow_redirects=False  # Don't follow redirects to see if login worked
            )
            
            print(f"Login response: {login_response.status_code}")
            
            # Check for successful login - either redirect (302) or no error message in response
            login_successful = False
            if login_response.status_code == 302:
                login_successful = True
                print("✅ Session authentication successful (redirect)")
            elif login_response.status_code == 200:
                # Check if the response contains error messages
                response_text = login_response.text.lower()
                if 'fel användarnamn' in response_text or 'error' in response_text or 'login' in response_text:
                    print(f"❌ Login failed - error in response")
                    print(f"   Response preview: {login_response.text[:200]}")
                    login_successful = False
                else:
                    login_successful = True
                    print("✅ Session authentication successful (200 OK)")
            
            if login_successful:
                
                # Try device registration with session
                session_response = session.post(
                    DEVICE_API_ENDPOINT,
                    json=registration_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=15
                )
                
                print(f"Session registration response: {session_response.status_code}")
                
                if session_response.status_code == 201:
                    data = session_response.json()
                    api_key = data['api_key']
                    print(f"✅ Device registered successfully!")
                    print(f"🔑 API Key: {api_key[:16]}...")
                    return api_key
                elif session_response.status_code == 409:
                    print("⚠️  Device already registered")
                    try:
                        data = session_response.json()
                        if 'api_key' in data:
                            print(f"🔑 Using existing API Key: {data['api_key'][:16]}...")
                            return data['api_key']
                    except:
                        pass
                    return None
                else:
                    print(f"❌ Session registration failed: {session_response.status_code}")
                    try:
                        error_data = session_response.json()
                        print(f"   Error: {error_data.get('error', 'Unknown error')}")
                    except:
                        print(f"   Response: {session_response.text[:200]}")
                    return None
            else:
                print(f"❌ Session login failed: {login_response.status_code}")
                if login_response.status_code == 200:
                    # Login page returned again - check for specific error
                    if 'fel användarnamn' in login_response.text.lower():
                        print("   Error: Wrong username or password")
                    elif 'csrf' in login_response.text.lower():
                        print("   Error: CSRF token issue")  
                    elif 'rate limit' in login_response.text.lower():
                        print("   Error: Rate limiting")
                    else:
                        print("   Error: Login form returned (check credentials)")
                print(f"   Response preview: {login_response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_api_key(self, api_key):
        """Save API key to device settings"""
        print(f"\n💾 Saving API key to device settings...")
        
        try:
            # Try to import settings manager
            sys.path.insert(0, str(self.project_root / "Settings"))
            from settings_manager import SettingsManager
            
            # Initialize settings manager
            settings = SettingsManager()
            
            # Save API key
            settings.set_setting('ota.api_key', api_key)
            
            # Also save OTA server URL if not set
            if not settings.get_setting('ota.server_url'):
                settings.set_setting('ota.server_url', OTA_SERVER_URL)
            
            print("✅ API key saved to settings")
            return True
            
        except ImportError as e:
            print(f"⚠️  Settings manager not available: {e}")
            print(f"✅ Registration successful! Manual setup required:")
            print(f"   API Key: {api_key}")
            print(f"   Server URL: {OTA_SERVER_URL}")
            print(f"\n💡 To complete setup:")
            print(f"   1. Save this API key in your camera's OTA settings")
            print(f"   2. Set OTA server URL to: {OTA_SERVER_URL}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving API key: {e}")
            print(f"✅ Registration successful! Manual setup required:")
            print(f"   API Key: {api_key}")
            print(f"   Server URL: {OTA_SERVER_URL}")
            return True
    
    def test_registration(self):
        """Test that the registration works by checking for updates"""
        print(f"\n🧪 Testing OTA registration...")
        
        try:
            # Import settings to get API key
            sys.path.insert(0, str(self.project_root / "Settings"))
            from settings_manager import SettingsManager
            
            settings = SettingsManager()
            api_key = settings.get_setting('ota.api_key')
            
            if not api_key:
                print("❌ No API key found in settings")
                return False
            
            # Test update check
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            test_data = {
                'cpu_id': self.cpu_id,
                'current_version': '0.0.0',
                'update_group': 'production'
            }
            
            response = requests.post(
                UPDATE_API_ENDPOINT,
                json=test_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ OTA system responding correctly")
                if data.get('update_available'):
                    print(f"   📦 Update available: {data.get('latest_version')}")
                else:
                    print("   📋 No updates available (normal)")
                return True
            else:
                print(f"❌ OTA test failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ OTA test error: {e}")
            return False
    
    def cleanup_secrets(self):
        """Clean up admin credentials from device after registration"""
        print(f"\n🧹 Cleaning up admin credentials...")
        
        try:
            # Simply remove the credentials file
            if self.credentials_file.exists():
                self.credentials_file.unlink()
                print(f"✅ Admin credentials file removed")
            else:
                print(f"✅ No credentials file to clean up")
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning up credentials: {e}")
            return False
    
    def run_setup(self):
        """Run complete OTA setup process"""
        print("🚀 Starting PyRpiCamController OTA Setup")
        print("="*50)
        
        # Check if running as root
        if os.geteuid() != 0:
            print("❌ This script must be run with sudo")
            return False
        
        # Step 1: Get device identification
        print("\n1️⃣ Gathering device information...")
        if not self.get_cpu_id():
            return False
        self.get_device_info()
        
        # Step 2: Load admin credentials
        print("\n2️⃣ Loading admin credentials...")
        username, password = self.load_admin_credentials()
        if not username or not password:
            return False
        
        # Step 3: Register device
        print("\n3️⃣ Registering device...")
        api_key = self.register_device(username, password)
        if not api_key:
            return False
        
        # Step 4: Save API key
        print("\n4️⃣ Saving configuration...")
        if not self.save_api_key(api_key):
            return False
        
        # Step 5: Test registration
        print("\n5️⃣ Testing registration...")
        if not self.test_registration():
            print("⚠️  Registration test failed, but API key is saved")
        
        # Step 6: Clean up
        print("\n6️⃣ Cleaning up...")
        self.cleanup_secrets()
        
        print("\n" + "="*50)
        print("✅ OTA Setup Complete!")
        print(f"   Device ID: {self.cpu_id}")
        print(f"   Name: {self.device_info['device_name']}")
        print(f"   OTA Server: {OTA_SERVER_URL}")
        print("\n💡 The device will now check for updates automatically")
        print("   You can also manually trigger updates using the update manager")
        
        return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        return
    
    setup = OTASetup()
    success = setup.run_setup()
    
    if not success:
        print("\n❌ OTA setup failed!")
        print("   Check the errors above and try again")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")

if __name__ == "__main__":
    main()