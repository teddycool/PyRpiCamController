# ImagePublisher Backend System

This directory contains the server-side backend for receiving and storing images and log data from PyRpiCamController cameras.

## Directory Structure

```
ImagePublisher/
├── api/                  # Data receiving endpoints
│   ├── receive_and_store_image_data.php # Image upload handling
│   ├── post_logitem.php             # Basic log data reception
│   └── post_logitem_secure.php      # Secure log data reception
├── database/             # Database setup and schema  
│   └── logging_schema.sql # Database schema for logs and images
└── utils/                # Configuration and utilities
    ├── config.php        # Database connection & settings
    ├── secrets.php       # Secret keys (git-ignored, copy from template)
    └── secrets_tmpl.php  # Template for secrets configuration
```

## Features

- Image upload and storage with automatic thumbnails
- Organized file structure by device and date
- Log data collection and storage
- Metadata preservation
- Basic security validation

## File Organization

Images are stored in the following structure:
```
/cvimages/
├── {cpu_id}/
│   ├── latest.jpg        # Most recent image
│   └── {date}/           # Date-based folders (YYYY-MM-DD)
│       ├── {timestamp}.jpg # Full resolution images
│       ├── {timestamp}.json # Image metadata
│       └── thumbs/       # Thumbnail images
│           └── {timestamp}.jpg
```

## API Endpoints

- `POST api/receive_and_store_image_data.php?cpu=XXX&meta=YYY` - Upload image with metadata
- `POST api/post_logitem.php?cpuid=XXX&...` - Submit log entry (basic)
- `POST api/post_logitem_secure.php` - Submit log entry (with validation)

## Database Tables

- **Camlog**: Stores log entries from camera devices
- **image_uploads**: Optional metadata tracking for uploaded images

## Installation

1. Set up MySQL database
2. Run `database/logging_schema.sql` to create tables
3. Copy `utils/secrets_tmpl.php` to `utils/secrets.php`
4. Configure `utils/secrets.php` with your database credentials and security keys
5. Configure `utils/config.php` with your environment settings
6. Ensure web server has write permissions to image storage directory
7. Set appropriate file permissions for `secrets.php`
8. Configure proper security measures for production use

## Security Considerations

- Implement proper CPU ID validation using `DEVICE_AUTH_KEY` from secrets
- Use API key authentication with `API_SECRET_KEY`
- Validate file types and sizes (configured in `secrets.php`)
- Configure appropriate file permissions
- Ensure `secrets.php` is not publicly accessible
- Use HTTPS for production deployment
- Regularly rotate API keys and authentication tokens