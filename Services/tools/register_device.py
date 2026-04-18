#!/usr/bin/env python3
"""
Device Registration Tool for PyRpiCamController OTA System

This tool helps register Raspberry Pi devices in the OTA update system from a development computer.
It can register single devices or batch register multiple devices from a list of CPU IDs.

Usage:
    # Single device registration
    python3 register_device.py --cpu-id "b827eb123456789a" --name "Camera 01" --location "Kitchen"
    
    # Batch registration from list
    python3 register_device.py --file devices.json
    
    # Batch registration from command line
    python3 register_device.py --cpu-ids "b827eb123456789a,20000000e5f6g7h8,30000000i9j0k1l2"
"""

import json
import requests
import argparse
import sys
from pathlib import Path
import os

# OTA Server Configuration
OTA_SERVER_URL = "https://www.sensorwebben.se/pycamota"
API_ENDPOINT = f"{OTA_SERVER_URL}/api/device_management.php"

def load_admin_credentials():
    """Load admin credentials from configuration file"""
    # Look for credentials in multiple locations
    config_paths = [
        Path(__file__).parent / "ota_config.json",
        Path.home() / ".pycamcontroller" / "ota_config.json",
        Path("/tmp/ota_config.json")
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                return config.get('admin_username', 'admin'), config.get('admin_password')
            except Exception as e:
                print(f"Warning: Could not read config from {config_path}: {e}")
                continue
    
    # Fallback to environment variables
    username = os.environ.get('OTA_ADMIN_USERNAME', 'admin')
    password = os.environ.get('OTA_ADMIN_PASSWORD')
    
    if not password:
        print("Error: Admin password not found in config file or environment variables")
        print("Please set OTA_ADMIN_PASSWORD environment variable or create ota_config.json")
        sys.exit(1)
    
    return username, password

def authenticate_admin():
    """Authenticate with admin interface and return session"""
    session = requests.Session()
    
    try:
        # Load credentials from config
        username, password = load_admin_credentials()
        
        # Login to admin interface
        login_url = f"{OTA_SERVER_URL}/admin/admin_auth.php"
        login_data = {
            'username': username,
            'password': password
        }
        
        response = session.post(login_url, data=login_data, timeout=30)
        
        if response.status_code == 200:
            print("✅ Admin authentication successful")
            return session
        else:
            print(f"❌ Admin authentication failed: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def validate_cpu_id(cpu_id):
    """Validate CPU ID format"""
    if not cpu_id:
        return False
    
    # Remove any prefixes like "0x" or "0000"
    clean_id = cpu_id.lower().replace('0x', '')
    
    # Should be 8 to 16 hex characters (Raspberry Pi CPU IDs can vary)
    if len(clean_id) < 8 or len(clean_id) > 16:
        return False
    
    try:
        int(clean_id, 16)
        return True
    except ValueError:
        return False

def register_device(session, cpu_id, device_name=None, location=None, update_group="production"):
    """Register a device with the OTA server using authenticated session"""
    
    if not validate_cpu_id(cpu_id):
        print(f"ERROR: Invalid CPU ID format: {cpu_id}")
        return None
    
    # Clean the CPU ID  
    clean_cpu_id = cpu_id.lower().replace('0x', '').zfill(16)
    
    try:
        print(f"📱 Registering device {clean_cpu_id}...")
        print(f"   Name: {device_name or 'N/A'}")
        print(f"   Location: {location or 'N/A'}")
        print(f"   Update Group: {update_group}")
        
        # First, try to register using POST with JSON (RESTful API)
        registration_data = {
            "cpu_id": clean_cpu_id,
            "update_group": update_group
        }
        
        if device_name:
            registration_data["device_name"] = device_name
        if location:
            registration_data["location"] = location
            
        response = session.post(
            API_ENDPOINT,
            json=registration_data,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"   ✅ Registered successfully!")
            print(f"   🔑 API Key: {data['api_key']}")
            
            return {
                'cpu_id': data['cpu_id'],
                'api_key': data['api_key'],
                'device_name': device_name,
                'location': location,
                'update_group': data['update_group']
            }
            
        elif response.status_code == 409:
            print(f"   ⚠️  Device already registered")
            return None
        elif response.status_code == 404:
            print(f"   ⚠️  RESTful API not available, trying alternative method...")
            # Fall back to query parameter method - this would require direct database access
            print(f"   ❌ Registration via admin interface requires manual setup")
            return None
        else:
            print(f"   ❌ Registration failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
                if 'details' in error_data:
                    print(f"   Details: {error_data['details']}")
            except:
                print(f"   Response: {response.text[:200]}")
            return None
    
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Could not connect to OTA server")
        return None
    except requests.exceptions.Timeout:
        print(f"   ❌ Connection timeout")
        return None
    except Exception as e:
        print(f"   ❌ Registration error: {e}")
        return None

def load_devices_from_file(file_path):
    """Load device list from JSON file"""
    try:
        with open(file_path, 'r') as f:
            devices = json.load(f)
        
        # Validate format
        if not isinstance(devices, list):
            print(f"❌ Invalid file format: expected list of devices")
            return None
        
        for device in devices:
            if 'cpu_id' not in device:
                print(f"❌ Invalid device format: missing cpu_id")
                return None
        
        return devices
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None

def save_registered_devices(devices):
    """Save registered device configurations to file"""
    try:
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        config_file = f"registered_devices_{timestamp}.json"
        
        config_data = {
            "registered_at": __import__('datetime').datetime.now().isoformat(),
            "ota_server": OTA_SERVER_URL,
            "devices": devices
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"\n📁 Device configurations saved to: {config_file}")
        print("This file contains API keys for all registered devices.")
        
    except Exception as e:
        print(f"\n⚠️  Could not save configuration: {e}")

def batch_register_devices(session, devices):
    """Register multiple devices from a list"""
    print(f"\n🚀 Starting batch registration of {len(devices)} device(s)")
    print("=" * 50)
    
    registered_devices = []
    
    for i, device in enumerate(devices, 1):
        print(f"\n[{i}/{len(devices)}] Processing device...")
        
        result = register_device(
            session=session,
            cpu_id=device['cpu_id'],
            device_name=device.get('device_name'),
            location=device.get('location'),
            update_group=device.get('update_group', 'production')
        )
        
        if result:
            registered_devices.append(result)
    
    return registered_devices

def main():
    parser = argparse.ArgumentParser(description="Register Raspberry Pi devices with OTA server from development computer")
    
    # Single device options
    parser.add_argument('--cpu-id', type=str, 
                       help='Single CPU ID to register (16 hex characters)')
    parser.add_argument('--name', type=str, 
                       help='Friendly device name (for single device)')
    parser.add_argument('--location', type=str, 
                       help='Device location description (for single device)')
    
    # Batch registration options
    parser.add_argument('--cpu-ids', type=str,
                       help='Comma-separated list of CPU IDs to register')
    parser.add_argument('--file', type=str,
                       help='JSON file containing device list to register')
    
    # Common options
    parser.add_argument('--update-group', type=str, default='production',
                       choices=['production', 'beta', 'development'],
                       help='Update group for devices')
    parser.add_argument('--test', action='store_true',
                       help='Test mode - use development update group')
    
    args = parser.parse_args()
    
    if args.test:
        args.update_group = 'development'
    
    print("🚀 PyRpiCamController OTA Device Registration Tool")
    print("=" * 50)
    
    # Authenticate with admin interface
    session = authenticate_admin()
    if not session:
        print("❌ Failed to authenticate with admin interface")
        sys.exit(1)
    
    devices_to_register = []
    
    # Determine what to register
    if args.cpu_id:
        # Single device
        devices_to_register = [{
            'cpu_id': args.cpu_id,
            'device_name': args.name,
            'location': args.location,
            'update_group': args.update_group
        }]
    elif args.cpu_ids:
        # Multiple CPU IDs from command line
        cpu_ids = [cpu_id.strip() for cpu_id in args.cpu_ids.split(',')]
        devices_to_register = []
        for i, cpu_id in enumerate(cpu_ids, 1):
            devices_to_register.append({
                'cpu_id': cpu_id,
                'device_name': f"Camera-{i:02d}",
                'location': f"Location-{i}",
                'update_group': args.update_group
            })
    elif args.file:
        # Load from JSON file
        devices_to_register = load_devices_from_file(args.file)
        if not devices_to_register:
            sys.exit(1)
        # Apply update group to all devices if not specified
        for device in devices_to_register:
            if 'update_group' not in device:
                device['update_group'] = args.update_group
    else:
        parser.print_help()
        print("\nError: You must specify one of: --cpu-id, --cpu-ids, or --file")
        sys.exit(1)
    
    # Register the devices
    if len(devices_to_register) == 1:
        # Single device
        device = devices_to_register[0]
        result = register_device(
            session=session,
            cpu_id=device['cpu_id'],
            device_name=device['device_name'],
            location=device['location'],
            update_group=device['update_group']
        )
        
        if result:
            print("\n🎉 Device registered successfully!")
            save_registered_devices([result])
        else:
            print("\n💥 Registration failed")
            sys.exit(1)
    else:
        # Batch registration
        registered_devices = batch_register_devices(session, devices_to_register)
        
        print(f"\n📊 Registration Summary:")
        print(f"   Total devices: {len(devices_to_register)}")
        print(f"   Successfully registered: {len(registered_devices)}")
        print(f"   Failed/Skipped: {len(devices_to_register) - len(registered_devices)}")
        
        if registered_devices:
            save_registered_devices(registered_devices)
            print("\n🎉 Batch registration completed!")
        else:
            print("\n💥 No devices were registered")
            sys.exit(1)
    
    print("\nNext steps:")
    print("1. Deploy the registered device configurations to your Raspberry Pi devices")
    print("2. Install the OTA update service on each device")
    print("3. Test the update process")
    print(f"4. Monitor devices at: {OTA_SERVER_URL}/admin/")

if __name__ == "__main__":
    main()