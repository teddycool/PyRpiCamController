#!/usr/bin/env python3
"""
Simplified Device Initialization for PyRpiCamController

This script is designed to run on a Pi during first boot or initial setup.
It handles the device registration automatically without requiring manual intervention.

Two modes:
1. Auto-registration: Uses a master API key to self-register
2. Pre-provisioned: Uses a pre-created settings.json with device API key

Usage:
    # Auto-registration mode (requires master API key)
    sudo python3 init_device.py --auto-register
    
    # Pre-provisioned mode (uses existing settings.json)
    sudo python3 init_device.py --pre-provisioned
    
    # Custom device info
    sudo python3 init_device.py --auto-register --name "Kitchen-Cam" --location "Kitchen"
"""

import json
import requests
import sys
import os
import subprocess
import argparse
from pathlib import Path
import socket

class DeviceInitializer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.settings_path = self.project_root / "Settings" / "settings.json"
        self.settings_schema = self.project_root / "Settings" / "settings_schema.json"
        self.ota_server_url = "https://www.sensorwebben.se/pycamota"
        self.cpu_id = None
        
    def get_cpu_id(self):
        """Get the Raspberry Pi CPU serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'Serial' in line:
                        serial = line.split(':')[1].strip()
                        clean_serial = serial.lower().replace('0x', '').zfill(16)
                        self.cpu_id = clean_serial
                        return clean_serial
            
            print("❌ Could not find CPU serial in /proc/cpuinfo")
            return None
        except Exception as e:
            print(f"❌ Error reading CPU info: {e}")
            return None
    
    def get_device_info(self, device_name=None, location=None):
        """Gather device information"""
        try:
            hostname = socket.gethostname()
            
            if not device_name:
                device_name = f"CamController-{hostname}"
            
            if not location:
                # Try to infer from hostname
                if 'kitchen' in hostname.lower():
                    location = "Kitchen"
                elif 'living' in hostname.lower():
                    location = "Living Room"
                elif 'bedroom' in hostname.lower():
                    location = "Bedroom"
                elif 'office' in hostname.lower():
                    location = "Office"
                else:
                    location = hostname.title()
            
            return {
                'device_name': device_name,
                'location': location,
                'hostname': hostname
            }
            
        except Exception as e:
            print(f"❌ Error gathering device info: {e}")
            return {
                'device_name': device_name or "Unknown",
                'location': location or "Unknown",
                'hostname': "unknown"
            }
    
    def auto_register_device(self, device_name=None, location=None, update_group="production"):
        """Auto-register this device using master credentials"""
        
        if not self.get_cpu_id():
            return False
        
        device_info = self.get_device_info(device_name, location)
        
        print(f"📱 Auto-registering device:")
        print(f"   CPU ID: {self.cpu_id}")
        print(f"   Name: {device_info['device_name']}")
        print(f"   Location: {device_info['location']}")
        print(f"   Group: {update_group}")
        
        # Try to register using the registration API
        try:
            # This would use a master API key or service account
            # For security, this should be configurable and use environment variables
            master_credentials = self.load_master_credentials()
            
            if not master_credentials:
                print("❌ Master credentials not available")
                return False
            
            registration_data = {
                "action": "register",
                "cpu_id": self.cpu_id,
                "device_name": device_info['device_name'],
                "location": device_info['location'],
                "update_group": update_group
            }
            
            response = requests.post(
                f"{self.ota_server_url}/api/device_management.php",
                json=registration_data,
                auth=(master_credentials['username'], master_credentials['password']),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                device_data = response.json()
                api_key = device_data['api_key']
                
                print(f"✅ Registration successful!")
                print(f"🔑 API Key: {api_key[:8]}...")
                
                # Create and save settings
                self.create_settings_with_api_key(api_key)
                return True
                
            elif response.status_code == 409:
                print("⚠️  Device already registered")
                # Could try to retrieve existing API key here
                return False
            else:
                print(f"❌ Registration failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def load_master_credentials(self):
        """Load master credentials for auto-registration"""
        # Priority order: environment variables, config file, hardcoded fallback
        
        username = os.environ.get('OTA_MASTER_USERNAME')
        password = os.environ.get('OTA_MASTER_PASSWORD')
        
        if username and password:
            return {'username': username, 'password': password}
        
        # Check for deployment-time credentials file
        creds_file = Path(__file__).parent / "deployment_credentials.txt"
        if creds_file.exists():
            try:
                with open(creds_file, 'r') as f:
                    lines = f.read().strip().split('\n')
                    if len(lines) >= 2:
                        return {'username': lines[0], 'password': lines[1]}
            except Exception as e:
                print(f"Warning: Could not read credentials file: {e}")
        
        # No credentials available
        return None
    
    def create_settings_with_api_key(self, api_key):
        """Create settings.json with the provided API key"""
        
        # Load default settings schema
        with open(self.settings_schema, 'r') as f:
            settings = json.load(f)
        
        # Enable OTA and set API key
        settings['settings']['OtaEnable']['value'] = True
        settings['settings']['OTA']['api_key']['value'] = api_key
        
        # Save to settings.json
        os.makedirs(self.settings_path.parent, exist_ok=True)
        with open(self.settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        print(f"⚙️  Settings saved to {self.settings_path}")
    
    def validate_pre_provisioned(self):
        """Validate that pre-provisioned settings are correct"""
        
        if not self.settings_path.exists():
            print(f"❌ Settings file not found: {self.settings_path}")
            return False
        
        try:
            with open(self.settings_path, 'r') as f:
                settings = json.load(f)
            
            # Check that OTA is enabled and API key is set
            ota_enabled = settings.get('settings', {}).get('OtaEnable', {}).get('value', False)
            api_key = settings.get('settings', {}).get('OTA', {}).get('api_key', {}).get('value', '')
            
            if not ota_enabled:
                print("❌ OTA not enabled in settings")
                return False
            
            if not api_key or api_key == "":
                print("❌ API key not set in settings")
                return False
            
            print(f"✅ Pre-provisioned settings validated")
            print(f"🔑 API Key: {api_key[:8]}...")
            return True
            
        except Exception as e:
            print(f"❌ Error validating settings: {e}")
            return False
    
    def setup_system_services(self):
        """Setup and start system services"""
        
        print("🔧 Setting up system services...")
        
        try:
            # Ensure proper permissions
            subprocess.run(['sudo', 'chown', '-R', 'pi:pi', str(self.project_root)], check=True)
            
            # Enable and start the camera controller service
            subprocess.run(['sudo', 'systemctl', 'enable', 'camcontroller.service'], check=True)
            subprocess.run(['sudo', 'systemctl', 'start', 'camcontroller.service'], check=True)
            
            print("✅ Services configured and started")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Service setup failed: {e}")
            return False
    
    def test_ota_connection(self):
        """Test that OTA system is working"""
        
        print("🧪 Testing OTA connection...")
        
        try:
            # Import settings manager to test configuration
            sys.path.append(str(self.project_root / "Settings"))
            from settings_manager import SettingsManager
            
            sm = SettingsManager()
            api_key = sm.get('OTA.api_key')
            
            if not api_key:
                print("❌ API key not loaded from settings")
                return False
            
            # Test update check
            check_url = f"{self.ota_server_url}/api/ota_check.php"
            response = requests.post(
                check_url,
                json={"api_key": api_key},
                timeout=15
            )
            
            if response.status_code == 200:
                print("✅ OTA connection test successful")
                return True
            else:
                print(f"❌ OTA connection test failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ OTA test error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Initialize PyRpiCamController device')
    parser.add_argument('--auto-register', action='store_true', help='Auto-register device')
    parser.add_argument('--pre-provisioned', action='store_true', help='Use pre-provisioned settings')
    parser.add_argument('--name', help='Device name override')
    parser.add_argument('--location', help='Device location override')
    parser.add_argument('--update-group', default='production', help='Update group')
    parser.add_argument('--skip-services', action='store_true', help='Skip service setup')
    parser.add_argument('--skip-test', action='store_true', help='Skip OTA test')
    
    args = parser.parse_args()
    
    if not (args.auto_register or args.pre_provisioned):
        print("❌ Must specify either --auto-register or --pre-provisioned")
        parser.print_help()
        sys.exit(1)
    
    # Ensure running as root for system setup
    if os.geteuid() != 0:
        print("❌ This script must be run with sudo for system setup")
        sys.exit(1)
    
    initializer = DeviceInitializer()
    
    print("🚀 Initializing PyRpiCamController device...")
    print("=" * 50)
    
    success = False
    
    if args.auto_register:
        success = initializer.auto_register_device(
            args.name, 
            args.location, 
            args.update_group
        )
    elif args.pre_provisioned:
        success = initializer.validate_pre_provisioned()
    
    if not success:
        print("\n❌ Device initialization failed")
        sys.exit(1)
    
    if not args.skip_services:
        if not initializer.setup_system_services():
            print("\n⚠️  Service setup failed, but device is registered")
    
    if not args.skip_test:
        if not initializer.test_ota_connection():
            print("\n⚠️  OTA test failed, but device is configured")
    
    print("\n✅ Device initialization complete!")
    print("🎯 PyRpiCamController is ready for operation")

if __name__ == "__main__":
    main()