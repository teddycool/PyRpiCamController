# PyRpiCamController Backend Systems

This directory contains server-side backend components for the PyRpiCamController project, organized into separate subsystems.

## Directory Structure

```
backend/
├── Updates/              # Updates System Backend
│   ├── api/             # Update check and management APIs
│   ├── admin/           # Web administration interface  
│   ├── database/        # Database schema and setup
│   ├── utils/           # Configuration and utilities
│   │   ├── config.php   # Main configuration
│   │   ├── secrets.php  # Secrets (git-ignored)
│   │   └── secrets_tmpl.php # Secrets template
│   └── README.md        # Updates system documentation
│
├── ImagePublisher/       # Image Publishing System Backend
│   ├── api/             # Image upload and log reception
│   ├── database/        # Database schema for logging
│   ├── utils/           # Configuration and utilities  
│   │   ├── config.php   # Main configuration
│   │   ├── secrets.php  # Secrets (git-ignored) 
│   │   └── secrets_tmpl.php # Secrets template
│   └── README.md        # Image publisher documentation
│
├── shared/              # Shared configurations (optional)
│   └── .htaccess        # Apache configuration
│
├── BACKEND.adoc         # Legacy documentation (to be updated)
└── README.md            # This file
```

## Systems Overview

### 🔄 Updates System
Manages over-the-air updates for deployed camera devices:
- Device registration and authentication
- Version management and distribution  
- Update status tracking
- Administrative web interface
- Supports device grouping and staged rollouts

### 📷 ImagePublisher System  
Handles image uploads and logging from camera devices:
- Image reception and storage with thumbnails
- Organized file structure by device/date
- Log data collection and database storage
- Metadata preservation

## Deployment

Both systems can be deployed independently or together:

- **Updates System**: Deploy to `/camcontroller-updates/` subdirectory
- **ImagePublisher**: Deploy to main domain or subdirectory
- **Database**: Can share database server or use separate instances

### Configuration Setup

1. **Copy secrets templates**: 
   ```bash
   cp backend/Updates/utils/secrets_tmpl.php backend/Updates/utils/secrets.php
   cp backend/ImagePublisher/utils/secrets_tmpl.php backend/ImagePublisher/utils/secrets.php
   ```

2. **Configure secrets**: Edit each `secrets.php` file with your database credentials and security keys

3. **Set permissions**: Ensure `secrets.php` files are readable by web server but not publicly accessible

**Note**: `secrets.php` files are git-ignored and will not be committed to version control.

## Migration Notes

This reorganization separates two distinct functionalities that were previously mixed:
1. Update management → `Updates/`
2. Image/log data publishing → `ImagePublisher/`

Each system now has its own:
- Database schema
- Configuration files  
- API endpoints
- Documentation
- Installation procedures

## Next Steps

1. Test the reorganized structure
2. Update any external references to moved files
3. Clean up legacy files in root directory
4. Update deployment scripts if needed