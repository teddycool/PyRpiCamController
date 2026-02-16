# Device Provisioning and Deployment Guide

This guide describes the recommended workflow for deploying PyRpiCamController to new hardware with unique API keys and automatic database registration.

## Overview

The deployment process follows a **"Provision-Deploy-Register"** pattern that separates device provisioning (done on your dev computer) from device deployment (done on the Pi). This ensures security and scalability.

## Workflow Options

### Option 1: Pre-Provisioning (Recommended for Production)

**Best for:** Production deployments, security-conscious environments, bulk deployment

#### Step 1: Provision Devices (Dev Computer)

```bash
# Single device provisioning
python3 tools/provision_devices.py --cpu-id "b827eb123456789a" --name "Kitchen Camera" --location "Kitchen"

# Batch provisioning from CSV
python3 tools/provision_devices.py --batch tools/device_batch_template.csv

# Auto-generate test devices
python3 tools/provision_devices.py --count 5 --prefix "Test-Cam"
```

This creates deployment packages in `tools/deployments/` containing:
- `settings.json` - Device-specific configuration with API key
- `deploy.sh` - Automated deployment script
- `device_info.json` - Device metadata
- `README.md` - Deployment instructions

#### Step 2: Deploy to Hardware

Copy the device-specific package to the Pi and run:

```bash
# On the Raspberry Pi
sudo ./deploy.sh
```

#### Step 3: Verify (Optional)

```bash
sudo systemctl status camcontroller.service
python3 tools/init_device.py --pre-provisioned --skip-services --skip-test
```

### Option 2: Auto-Registration (Easier for Development)

**Best for:** Development, testing, small-scale deployments

#### Step 1: Setup Master Credentials

Create deployment credentials (use environment variables or config file):

```bash
# Set environment variables
export OTA_MASTER_USERNAME="admin"
export OTA_MASTER_PASSWORD="your_admin_password"

# Or create credentials file
echo -e "admin\nyour_admin_password" > tools/deployment_credentials.txt
```

#### Step 2: Auto-Register on Pi

```bash
# On the Raspberry Pi during first setup
sudo python3 tools/init_device.py --auto-register --name "Kitchen-Cam" --location "Kitchen"
```

This will:
1. Get the Pi's CPU ID automatically
2. Register with the backend using master credentials
3. Save the API key to settings
4. Setup and start services
5. Test OTA connection

## CSV File Format for Batch Provisioning

Create a CSV file with device information:

```csv
cpu_id,device_name,location,update_group,test_device
10000000a1b2c3d4,Kitchen Camera,Kitchen Counter,production,false
20000000e5f6g7h8,Living Room Camera,Living Room TV Stand,production,false
30000000i9j0k1l2,Outdoor Camera,Garden Entrance,beta,false
40000000m3n4o5p6,Test Camera 1,Development Lab,development,true
```

Required columns:
- `cpu_id` - Raspberry Pi CPU serial (get with `cat /proc/cpuinfo | grep Serial`)
- `device_name` - Friendly name for the device
- `location` - Physical location description  
- `update_group` - Update channel: production, beta, development
- `test_device` - Set to `true` for test hardware (enables development channel access)

## Security Considerations

### Pre-Provisioning Method (More Secure)
✅ API keys generated on secure dev computer  
✅ No master credentials stored on devices  
✅ Individual device compromise doesn't affect others  
✅ Audit trail of all provisioned devices  

### Auto-Registration Method (Less Secure)
⚠️ Master credentials needed on each device  
⚠️ Credentials should be removed after registration  
⚠️ Compromise of one device could affect others  

## Directory Structure

```
tools/
├── provision_devices.py          # Pre-provisioning tool (dev computer)
├── init_device.py               # Auto-registration tool (Pi)
├── device_batch_template.csv    # CSV template for batch provisioning
├── register_device.py           # Original registration tool
└── deployments/                 # Generated deployment packages
    └── deployment_20260216_143052/
        └── device_b827eb123456789a/
            ├── settings.json     # Device-specific settings
            ├── deploy.sh        # Deployment script
            ├── device_info.json # Device metadata
            └── README.md        # Instructions
```

## API Integration

The tools use your existing backend API endpoints:

- `POST /api/device_management.php` - Device registration
- `POST /api/ota_check.php` - Update checking
- Database table: `devices` (cpu_id, api_key, device_name, location)

## Best Practices

### For Production Deployment

1. **Use Pre-Provisioning:** Generate all device configs on secure dev computer
2. **Secure Transport:** Use encrypted storage/transmission for deployment packages  
3. **Cleanup:** Delete deployment packages after successful deployment
4. **Verify:** Test OTA connectivity after deployment
5. **Monitor:** Use the backend admin panel to monitor device status

### For Development/Testing

1. **Use Auto-Registration:** Faster setup with master credentials
2. **Test Groups:** Use `development` or `beta` update groups
3. **Batch Operations:** Use CSV files for multiple test devices
4. **Cleanup:** Remove test devices from database when done

### For Bulk Hardware Preparation

1. **Pre-Flash Images:** Include deployment packages in Pi images
2. **First-Boot Scripts:** Run deployment automatically on first boot
3. **QR Codes:** Generate QR codes with deployment URLs for field staff
4. **Status Reports:** Collect deployment success/failure status

### For Test Hardware

1. **Test Device Mode:** Use `--test-device` flag or set `test_device=true` in CSV
2. **Development Channel:** Test devices automatically get access to development updates
3. **Web GUI Access:** Test devices can select development channel in advanced settings
4. **Auto-Detection:** Devices with `update_group=development` are auto-flagged as test devices

**Test device provisioning:**
```bash
# Single test device
python3 tools/provision_devices.py --cpu-id "test0001000000000" --name "Test-Cam-1" --test-device

# Test device with development channel
python3 tools/provision_devices.py --cpu-id "test0002000000000" --update-group "development"

# Batch test devices from CSV (with test_device=true column)
python3 tools/provision_devices.py --batch test_devices.csv
```

## Troubleshooting

### Common Issues

**Device already registered:**
```bash
# Check existing registration
python3 tools/register_device.py --cpu-id "your_cpu_id" --list
```

**API key not working:**
```bash
# Test OTA connection
python3 tools/init_device.py --pre-provisioned --skip-services
```

**Service not starting:**
```bash
# Check service status
sudo systemctl status camcontroller.service
sudo journalctl -u camcontroller.service -f
```

### Manual Recovery

If automated deployment fails, you can manually:

1. Copy settings.json to `/home/pi/PyRpiCamController/Settings/`
2. Run the optimized installer: `sudo python3 tools/install-all-optimized.py`
3. Start services: `sudo systemctl enable --now camcontroller.service`

## Integration with Existing Tools

This workflow enhances your existing tools:
- **Uses** `register_device.py` for backend registration
- **Builds on** `setup_ota_registration.py` concepts  
- **Compatible with** existing `settings_schema.json`
- **Works with** current OTA update system
- **Integrates with** release manager workflow

The key improvement is separating device provisioning from deployment, making the process more secure and scalable for production use.