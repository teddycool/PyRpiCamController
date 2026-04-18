#!/usr/bin/env python3
"""
Manual Device Registration Tool for OTA Admin

This tool helps administrators register devices manually through the web interface.
It can be used to register devices that aren't physically accessible or for testing.
"""

import json
import requests
import sys

# OTA Admin Configuration
OTA_ADMIN_URL = "https://www.sensorwebben.se/pycamota/admin"
OTA_API_URL = "https://www.sensorwebben.se/pycamota/api/devices"

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "K7#mN9@pQ4*vX2!wZ8$rF6&hL3^dS5"

def authenticate_admin():
    """Authenticate with admin interface"""
    session = requests.Session()
    
    try:
        # Login to admin interface
        login_data = {
            'username': ADMIN_USERNAME,
            'password': ADMIN_PASSWORD
        }
        
        response = session.post(
            f"{OTA_ADMIN_URL}/admin_auth.php",
            data=login_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Admin authentication successful")
            return session
        else:
            print(f"❌ Admin authentication failed: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def register_test_devices(session):
    """Register several test devices for demonstration"""
    
    test_devices = [
        {
            "cpu_id": "10000000a1b2c3d4",
            "device_name": "Test Kitchen Camera",
            "location": "Kitchen Counter",
            "update_group": "production"
        },
        {
            "cpu_id": "20000000e5f6g7h8",
            "device_name": "Test Living Room Camera", 
            "location": "Living Room",
            "update_group": "beta"
        },
        {
            "cpu_id": "30000000i9j0k1l2",
            "device_name": "Test Outdoor Camera",
            "location": "Garden Entrance",
            "update_group": "production"
        },
        {
            "cpu_id": "40000000m3n4o5p6",
            "device_name": "Development Camera",
            "location": "Developer Desk",
            "update_group": "development"
        }
    ]
    
    registered_devices = []
    
    for device in test_devices:
        try:
            print(f"\n🔧 Registering device: {device['device_name']}")
            print(f"   CPU ID: {device['cpu_id']}")
            print(f"   Location: {device['location']}")
            print(f"   Update Group: {device['update_group']}")
            
            response = session.post(
                OTA_API_URL,
                json=device,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                print(f"   ✅ Registered successfully")
                print(f"   🔑 API Key: {result['api_key']}")
                
                registered_devices.append({
                    'device': device,
                    'api_key': result['api_key']
                })
                
            elif response.status_code == 409:
                print(f"   ⚠️  Device already exists")
            else:
                print(f"   ❌ Registration failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error registering device: {e}")
    
    return registered_devices

def list_devices(session):
    """List all registered devices"""
    try:
        print("\n📋 Listing all registered devices:")
        
        response = session.get(
            f"{OTA_API_URL}?action=list",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            devices = data.get('devices', [])
            
            if devices:
                print(f"\nFound {len(devices)} device(s):")
                for device in devices:
                    print(f"  📱 {device.get('device_name', 'Unnamed Device')}")
                    print(f"     CPU ID: {device['cpu_id']}")
                    print(f"     Location: {device.get('location', 'N/A')}")
                    print(f"     Version: {device.get('current_version', 'Unknown')}")
                    print(f"     Status: {device.get('status', 'Unknown')}")
                    print(f"     Update Group: {device.get('update_group', 'N/A')}")
                    print(f"     Last Seen: {device.get('last_seen', 'Never')}")
                    print()
            else:
                print("  No devices registered yet")
            
            # Show stats
            if 'total' in data:
                print(f"📊 Statistics:")
                print(f"   Total: {data['total']}")
                print(f"   Online: {data['online']}")  
                print(f"   Pending Updates: {data['pending']}")
                print(f"   Last Activity: {data['last_activity']}")
        else:
            print(f"❌ Failed to list devices: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error listing devices: {e}")

def save_device_config(registered_devices):
    """Save registered device configurations to file"""
    if not registered_devices:
        return
    
    try:
        config_file = "/tmp/ota_registered_devices.json"
        
        with open(config_file, 'w') as f:
            json.dump(registered_devices, f, indent=2)
        
        print(f"\n📁 Device configurations saved to: {config_file}")
        print("This file contains API keys for testing OTA updates.")
        
    except Exception as e:
        print(f"❌ Could not save device config: {e}")

def main():
    print("🚀 PyRpiCamController OTA Device Registration Tool")
    print("=" * 50)
    
    # Authenticate with admin interface
    session = authenticate_admin()
    if not session:
        print("Failed to authenticate with admin interface")
        sys.exit(1)
    
    # List existing devices first
    list_devices(session)
    
    # Register test devices
    print("\n" + "=" * 50)
    print("🔧 Registering Test Devices")
    registered_devices = register_test_devices(session)
    
    if registered_devices:
        print(f"\n✅ Successfully registered {len(registered_devices)} device(s)")
        save_device_config(registered_devices)
    else:
        print("\n⚠️  No new devices were registered")
    
    # List devices again to show results
    print("\n" + "=" * 50)
    print("📋 Final Device List")
    list_devices(session)
    
    print("\n🎉 Device registration completed!")
    print("\nNext steps:")
    print("1. Check the admin dashboard at: https://www.sensorwebben.se/pycamota/admin/")
    print("2. Configure actual Raspberry Pi devices with their API keys")
    print("3. Test the OTA update process")

if __name__ == "__main__":
    main()