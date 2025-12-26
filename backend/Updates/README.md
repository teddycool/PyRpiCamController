# Updates Backend System

This directory contains the server-side backend for the PyRpiCamController Over-The-Air (OTA) update system. The system handles **complete system updates** where each release contains the entire PyRpiCamController project structure.

## Update Approach

This system uses a **full system update approach** where:
- Each update package contains the complete PyRpiCamController system
- All components (CamController, WebGui, Settings, Services) are updated together
- Updates can be distributed via packaged files or git tags
- Services are restarted automatically after successful updates
- Automatic backup and rollback capabilities for failed updates

## Directory Structure

```
Updates/
├── api/                  # REST API endpoints
│   ├── ota_check.php     # Device update checking
│   ├── ota_report.php    # Status reporting
│   ├── device_management.php # Device CRUD operations  
│   ├── version_management.php # Version management
│   └── api_test.php      # API testing
├── admin/                # Web admin interface
│   ├── admin_dashboard.php # Main admin dashboard
│   ├── admin_login.php   # Login interface
│   ├── admin_logout.php  # Logout handling
│   └── admin_auth.php    # Authentication logic
├── database/             # Database setup and schema
│   ├── ota_schema.sql    # Complete database schema
│   ├── db_setup.php      # Database initialization
│   └── db_status.php     # Health checking
└── utils/                # Configuration and utilities
    ├── config.php        # Database connection & settings
    ├── secrets.php       # Secret keys (git-ignored, copy from template)
    ├── secrets_tmpl.php  # Template for secrets configuration
    └── simple_device_list.php # Simple device listing
```

## Features

- **Full System Updates**: Complete PyRpiCamController system updates
- **Git Integration**: Support for git tags and commit tracking
- **Multiple Distribution Methods**: Package files or git repository cloning
- **Automatic Service Management**: Restart required services after updates
- **Backup & Rollback**: Automatic backup creation and rollback on failure
- **Device Management**: Registration, grouping, and monitoring
- **Release Management**: Development → Testing → Stable promotion workflow
- **Administrative Interface**: Web-based dashboard for update management
- **Status Monitoring**: Detailed logging and update progress tracking
- **Device Grouping**: Deploy to production, beta, or development groups
- **Health Checks**: Pre and post-update validation

## Installation

1. Set up MySQL database
2. Run `database/ota_schema.sql` to create tables
3. Copy `utils/secrets_tmpl.php` to `utils/secrets.php`
4. Configure `utils/secrets.php` with your database credentials and admin password
5. Configure `utils/config.php` with your environment settings
6. Deploy to web server in subdirectory (e.g., `/pycamota/`)
7. Set appropriate file permissions for `secrets.php`

## API Endpoints

- `GET api/ota_check.php?cpu_id=XXX&api_key=YYY` - Check for system updates
- `POST api/ota_report.php` - Report update status and progress
- `GET/POST api/device_management.php` - Device CRUD operations
- `GET/POST api/version_management.php` - Full system version management

### Update Response Format

The update check returns complete system update information:

```json
{
  "update_available": true,
  "version": "1.1.0",
  "git_tag": "v1.1.0", 
  "git_commit_hash": "abc123...",
  "download_url": "https://example.com/releases/PyRpiCamController_v1.1.0.tar.gz",
  "git_clone_url": "https://github.com/user/PyRpiCamController.git",
  "checksum": "sha256...",
  "file_size": 15728640,
  "requires_reboot": false,
  "services_to_restart": ["camcontroller.service", "camcontroller-web.service"],
  "backup_required": true,
  "update_script": "install-all.py",
  "release_notes": "Major feature update...",
  "changelog": "Detailed changes..."
}
```

## Deployment Methods

The system supports multiple update deployment methods:

### 1. Package-Based Updates
- Download complete system as compressed archive
- Verify checksum for integrity
- Extract and replace system files
- Restart services as specified

### 2. Git-Based Updates  
- Clone from git repository using specified tag
- Checkout specific commit hash
- Run update scripts (install-all.py, etc.)
- Restart services automatically

### 3. Hybrid Approach
- Use package for initial deployment
- Switch to git for development updates
- Tag releases in git for version management

## Security

- API key authentication for device access
- Admin session management for web interface
- Input validation and SQL injection protection
- HTTPS recommended for production deployment