#!/usr/bin/env python3
"""
Device Provisioning Tool for PyRpiCamController

This tool pre-registers devices and generates deployment packages from your development computer.
Run this BEFORE deploying hardware to generate device-specific configurations.

Usage:
    # Single device
    python3 provision_devices.py --cpu-id "b827eb123456789a" --name "Kitchen Cam" --location "Kitchen"
    
    # Batch provision from CSV/JSON
    python3 provision_devices.py --batch devices.csv
    
    # Auto-provision N devices (for bulk deployment)
    python3 provision_devices.py --count 10 --prefix "Office-Cam"
"""

import json
import csv
import argparse
import requests
import sys
import os
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import uuid

# Import existing registration functionality
from register_device import authenticate_admin, register_device

class DeviceProvisioner:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.settings_schema = self.project_root / "Settings" / "settings_schema.json"
        self.deployment_dir = Path("deployments")
        self.deployment_dir.mkdir(exist_ok=True)
        
    def create_device_settings(self, api_key, cpu_id, device_name=None, location=None):
        """Create device-specific settings.json with embedded API key"""
        
        # Load default settings schema
        with open(self.settings_schema, 'r') as f:
            settings = json.load(f)
        
        # Customize for this device
        settings['settings']['OtaEnable']['value'] = True
        settings['settings']['OTA']['api_key']['value'] = api_key
        
        # Optional: Set device-specific defaults
        if device_name:
            # Could set hostname or other device-specific settings
            pass
        if location and 'kitchen' in location.lower():
            # Location-specific defaults (e.g., different image locations)
            settings['settings']['Cam']['publishers']['file']['location']['value'] = f"/home/pi/shared/images/{location.lower()}/"
        
        return settings
    
    def create_deployment_package(self, device_config, output_dir):
        """Create a complete deployment package for a device"""
        
        device_id = device_config['cpu_id']
        package_dir = output_dir / f"device_{device_id}"
        package_dir.mkdir(exist_ok=True)
        
        # 1. Create device-specific settings
        settings = self.create_device_settings(
            device_config['api_key'],
            device_config['cpu_id'],
            device_config.get('device_name'),
            device_config.get('location')
        )
        
        settings_file = package_dir / "settings.json"
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # 2. Create deployment script for this device
        deploy_script = f"""#!/bin/bash
# Deployment script for device {device_id}
# Generated: {datetime.now().isoformat()}

set -e

echo "🚀 Deploying PyRpiCamController for device {device_id}"

# Deployment variables
DEVICE_ID="{device_id}"
DEVICE_NAME="{device_config.get('device_name', 'Unknown')}"
LOCATION="{device_config.get('location', 'Unknown')}"

# Install base system
echo "📦 Installing base system..."
sudo python3 tools/install-all-optimized.py

# Copy device-specific settings
echo "⚙️  Configuring device settings..."
sudo cp settings.json /home/pi/PyRpiCamController/Settings/

# Start services
echo "🎯 Starting services..."
sudo systemctl enable camcontroller.service
sudo systemctl start camcontroller.service

# Test registration
echo "✅ Testing OTA registration..."
python3 -c "import sys; sys.path.append('/home/pi/PyRpiCamController/Settings'); from settings_manager import SettingsManager; sm = SettingsManager(); print('API Key configured:', bool(sm.get('OTA.api_key')))"

echo "✅ Deployment complete for $DEVICE_NAME at $LOCATION"
echo "💡 Device ID: $DEVICE_ID"
"""
        
        deploy_script_file = package_dir / "deploy.sh"
        with open(deploy_script_file, 'w') as f:
            f.write(deploy_script)
        deploy_script_file.chmod(0o755)
        
        # 3. Create device info file
        device_info = {
            **device_config,
            "deployment_created": datetime.now().isoformat(),
            "deployment_notes": "Auto-generated deployment package"
        }
        
        info_file = package_dir / "device_info.json"
        with open(info_file, 'w') as f:
            json.dump(device_info, f, indent=2)
        
        # 4. Create README
        readme_content = f"""# Device Deployment Package
        
**Device ID:** {device_id}
**Name:** {device_config.get('device_name', 'Unknown')}
**Location:** {device_config.get('location', 'Unknown')}
**Created:** {datetime.now().isoformat()}

## Deployment Instructions

1. Copy this entire folder to the Raspberry Pi
2. Run: `chmod +x deploy.sh && sudo ./deploy.sh`
3. Verify deployment with: `sudo systemctl status camcontroller.service`

## Files
- `settings.json` - Device-specific configuration with API key
- `deploy.sh` - Automated deployment script  
- `device_info.json` - Device metadata
- `README.md` - This file

## Security Note
The `settings.json` contains sensitive API keys. Keep secure and delete after deployment.
"""
        
        readme_file = package_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        return package_dir
    
    def provision_single_device(self, cpu_id, device_name=None, location=None, update_group="production"):
        """Provision a single device"""
        
        print(f"🔧 Provisioning device {cpu_id}...")
        
        # Authenticate and register with backend
        session = authenticate_admin()
        if not session:
            print("❌ Admin authentication failed")
            return None
            
        device_config = register_device(session, cpu_id, device_name, location, update_group)
        
        if not device_config:
            print(f"❌ Failed to register device {cpu_id}")
            return None
        
        # Create deployment package
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        deployment_dir = self.deployment_dir / f"deployment_{timestamp}"
        
        package_dir = self.create_deployment_package(device_config, deployment_dir)
        
        print(f"✅ Device provisioned successfully!")
        print(f"📦 Deployment package: {package_dir}")
        print(f"🔑 API Key: {device_config['api_key'][:8]}...")
        
        return {
            'device_config': device_config,
            'package_dir': package_dir
        }
    
    def provision_from_csv(self, csv_file):
        """Provision multiple devices from CSV file"""
        
        devices = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                devices.append({
                    'cpu_id': row['cpu_id'],
                    'device_name': row.get('device_name'),
                    'location': row.get('location'),
                    'update_group': row.get('update_group', 'production')
                })
        
        return self.provision_batch(devices)
    
    def provision_batch(self, devices):
        """Provision multiple devices"""
        
        print(f"🚀 Starting batch provisioning of {len(devices)} devices")
        
        # Authenticate once
        session = authenticate_admin()
        if not session:
            print("❌ Admin authentication failed")
            return []
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        deployment_dir = self.deployment_dir / f"batch_deployment_{timestamp}"
        
        results = []
        
        for i, device in enumerate(devices, 1):
            print(f"\n[{i}/{len(devices)}] Provisioning {device['cpu_id']}...")
            
            device_config = register_device(
                session,
                device['cpu_id'],
                device.get('device_name'),
                device.get('location'),
                device.get('update_group', 'production')
            )
            
            if device_config:
                package_dir = self.create_deployment_package(device_config, deployment_dir)
                results.append({
                    'device_config': device_config,
                    'package_dir': package_dir,
                    'success': True
                })
                print(f"   ✅ Provisioned with API key {device_config['api_key'][:8]}...")
            else:
                results.append({
                    'device': device,
                    'success': False,
                    'error': 'Registration failed'
                })
                print(f"   ❌ Failed to provision")
        
        # Create batch summary
        summary = {
            'timestamp': timestamp,
            'total_devices': len(devices),
            'successful': len([r for r in results if r['success']]),
            'failed': len([r for r in results if not r['success']]),
            'devices': [r['device_config'] if r['success'] else r['device'] for r in results]
        }
        
        summary_file = deployment_dir / "batch_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Batch provisioning complete!")
        print(f"📦 Deployment directory: {deployment_dir}")
        print(f"✅ Successful: {summary['successful']}")
        print(f"❌ Failed: {summary['failed']}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Provision devices for deployment')
    parser.add_argument('--cpu-id', help='Single device CPU ID')
    parser.add_argument('--name', help='Device name')
    parser.add_argument('--location', help='Device location')
    parser.add_argument('--update-group', default='production', help='Update group')
    parser.add_argument('--batch', help='CSV file with device list')
    parser.add_argument('--count', type=int, help='Auto-generate N devices (for testing)')
    parser.add_argument('--prefix', default='Test-Device', help='Prefix for auto-generated devices')
    
    args = parser.parse_args()
    
    provisioner = DeviceProvisioner()
    
    if args.cpu_id:
        # Single device
        provisioner.provision_single_device(
            args.cpu_id, 
            args.name, 
            args.location, 
            args.update_group
        )
    
    elif args.batch:
        # Batch from CSV
        provisioner.provision_from_csv(args.batch)
    
    elif args.count:
        # Auto-generate devices (for testing)
        devices = []
        for i in range(args.count):
            devices.append({
                'cpu_id': f"test{i:04d}000000000000",
                'device_name': f"{args.prefix}-{i+1:02d}",
                'location': f"Location-{i+1:02d}",
                'update_group': 'development'
            })
        provisioner.provision_batch(devices)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()