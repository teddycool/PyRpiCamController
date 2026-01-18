# PyRpiCamController Admin API & Dashboard Documentation

## Overview
The PyRpiCamController OTA (Over-The-Air) system consists of an admin dashboard for managing software versions and a REST API for Pi devices to check for and download updates.

## API Structure

### Base URLs
- **Admin Dashboard**: `https://your-domain.com/pycamota/admin/`
- **API Endpoints**: `https://your-domain.com/pycamota/api/`

### URL Routing (.htaccess)
```apache
# Version Management (via .htaccess rewriting)
/pycamota/api/versions -> /pycamota/api/version_management.php
/pycamota/api/versions/123 -> /pycamota/api/version_management.php?id=123

# Device Management
/pycamota/api/devices -> /pycamota/api/device_management.php

# OTA Check
/pycamota/api/ota/check -> /pycamota/api/ota_check.php
```

## Step 1: Version Upload Process (Primary Focus)

### 1.1 Admin Dashboard Upload Flow

```
[Admin Login] → [Dashboard] → [Upload Modal] → [File Select] → [Version Info] → [Submit]
     ↓              ↓             ↓              ↓              ↓              ↓
[Session Auth] → [Load UI] → [Form Display] → [File Valid.] → [Metadata] → [AJAX Request]
                                                                               ↓
                                                                        [version_management.php]
```

### 1.2 Upload Request Structure

**URL**: `POST /pycamota/api/versions?action=upload`

**Headers**:
```
Content-Type: multipart/form-data
Cookie: pycamota_admin=<session_id>
```

**Form Data**:
```
file: <binary file data> (PyRpiCamController-X.Y.Z.tar.gz)
metadata: {
  "version": "1.0.0",
  "description": "Version 1.0.0",
  "release_notes": "Initial release"
}
```

### 1.3 Server-Side Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    version_management.php                   │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Initialize admin session (start_admin_session())        │
│    - Set session name: 'pycamota_admin'                   │
│    - Configure secure session settings                     │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Check Upload Conditions                                 │
│    - $_SERVER['REQUEST_METHOD'] === 'POST'                │
│    - isset($_GET['action']) && $_GET['action'] === 'upload'│
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Authentication Check                                     │
│    - is_admin_authenticated()                              │
│    - Verify session data exists                           │
│    - Check session timeout                                 │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. File Upload Validation                                  │
│    - Check $_FILES['file'] exists                         │
│    - Verify upload error status                           │
│    - Check file size limits                               │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Metadata Processing                                     │
│    - Parse $_POST['metadata'] JSON                        │
│    - Validate required fields                             │
│    - Extract version, description, release_notes          │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. File Storage                                           │
│    - Create storage directory                             │
│    - Generate filename: PyRpiCamController-{version}.tar.gz│
│    - move_uploaded_file() to storage/versions/            │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Database Storage                                         │
│    - INSERT into versions table                             │
│    - Store: version, description, file_path, file_size    │
│    - Handle duplicate version errors                      │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Response Formats

**Success Response**:
```json
{
  "status": "success",
  "message": "Version uploaded successfully",
  "version": "1.0.0"
}
```

**Error Responses**:
```json
// Authentication Error
{
  "error": "Authentication required for upload"
}

// File Upload Error
{
  "error": "File upload error",
  "details": "File too large (exceeds upload_max_filesize)",
  "debug": { ... }
}

// Validation Error
{
  "error": "Version is required",
  "debug": { ... }
}

// Database Error
{
  "error": "Version already exists"
}
```

## Authentication System

### 1.5 Session Management

```
┌─────────────────────────────────────────────────────────────┐
│                   Admin Authentication                      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Session Configuration:                                      │
│ - Name: 'pycamota_admin'                                   │
│ - HTTPOnly: true                                           │
│ - Secure: depends on REQUIRE_HTTPS setting                │
│ - SameSite: 'Strict'                                       │
│ - Regeneration: every 5 minutes                           │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Session Data Structure:                                     │
│ - admin_authenticated: true                                │
│ - admin_username: "admin"                                  │
│ - admin_login_time: <timestamp>                            │
│ - admin_last_activity: <timestamp>                         │
│ - csrf_token: <random_token>                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.6 Authentication Flow

```
[Login Page] → [Credentials] → [Validation] → [Session Create] → [Dashboard Access]
     │             │              │              │                    │
     │             ▼              │              ▼                    ▼
     │      username/password      │      $_SESSION data         Cookie Set
     │             │              ▼              │                    │
     └─────────────┴──────→ ADMIN_USERNAME ──────┴──────→ pycamota_admin=<id>
                            ADMIN_PASSWORD_HASH
```

## Common Issues & Debugging

### 1.7 Upload Troubleshooting Flowchart

```
┌─────────────────────────────────────────────────────────────┐
│                Upload Request Fails                         │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Check 1: Is request reaching version_management.php?       │
│ Test: Add debug output at top of file                     │
│ URL: /pycamota/api/versions?action=upload                  │
└─────────────────────────────────────────────────────────────┘
                    │                        │
                    ▼ YES                    ▼ NO
┌────────────────────────────┐  ┌─────────────────────────────┐
│ Check 2: Authentication    │  │ Check .htaccess routing     │
│ Test: /api/versions?debug=auth│ Fix: Upload .htaccess to     │
│ Should show: authenticated │  │ /pycamota/ directory        │
└────────────────────────────┘  └─────────────────────────────┘
                    │
                    ▼ AUTH OK
┌─────────────────────────────────────────────────────────────┐
│ Check 3: Upload conditions met?                            │
│ - REQUEST_METHOD === 'POST'                                │
│ - $_GET['action'] === 'upload'                             │
│ - $_FILES['file'] exists                                   │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼ CONDITIONS OK
┌─────────────────────────────────────────────────────────────┐
│ Check 4: File upload limits                                │
│ - PHP upload_max_filesize                                  │
│ - PHP post_max_size                                        │
│ - PHP max_execution_time                                   │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼ LIMITS OK
┌─────────────────────────────────────────────────────────────┐
│ Check 5: Directory permissions                             │
│ - storage/versions/ writable                               │
│ - Database connection works                                │
│ - Database table exists                                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.8 Debugging Commands

**Check if file changes take effect**:
```bash
# Add timestamp to file, upload, then test:
curl "https://your-domain.com/pycamota/api/versions?debug=test"
```

**Check authentication status**:
```bash
# Login to admin dashboard first, then:
curl "https://your-domain.com/pycamota/api/versions?debug=auth"
```

**Check upload conditions**:
```bash
# Add debug output to show $_GET, $_POST, $_FILES:
curl -X POST "https://your-domain.com/pycamota/api/versions?action=upload" \
     -F "file=@test.tar.gz" \
     -F "metadata={\"version\":\"test\"}"
```

## Database Schema

### 1.9 Versions Table Structure

```sql
CREATE TABLE versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    file_path VARCHAR(255) NOT NULL,
    file_size BIGINT,
    release_notes TEXT,
    release_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'inactive', 'beta') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## File Structure

### 1.10 Directory Layout

```
/pycamota/
├── .htaccess                    # URL routing rules
├── api/
│   ├── version_management.php   # Version upload/management
│   ├── device_management.php    # Device registration
│   ├── ota_check.php           # Pi update checks
│   └── config.php              # Database connection
├── admin/
│   ├── admin_dashboard.php     # Upload interface
│   ├── admin_login.php         # Login form
│   └── admin_auth.php          # Authentication functions
├── storage/
│   └── versions/               # Uploaded release files
│       └── PyRpiCamController-1.0.0.tar.gz
└── utils/
    └── secrets.php             # Database credentials
```

## Cache Issues

### 1.11 PHP Caching Problems

**Symptoms**:
- File uploads but code changes don't take effect
- Old responses despite file modifications
- Debug output doesn't appear

**Solutions**:
```php
// Add to top of PHP file:
if (function_exists('opcache_invalidate')) {
    opcache_invalidate(__FILE__, true);
}
if (function_exists('opcache_reset')) {
    opcache_reset();
}
```

**Server-level solutions**:
- Restart Apache/PHP-FPM
- Clear OPcache via hosting control panel
- Create new file with different name (bypasses cache)

## Testing Checklist

### 1.12 Upload Functionality Test

- [ ] Admin login works
- [ ] Dashboard loads properly
- [ ] Upload modal appears
- [ ] File selection works
- [ ] Version validation works
- [ ] Authentication persists during upload
- [ ] File actually uploads to server
- [ ] Database record created
- [ ] Success message displays
- [ ] File appears in storage directory
- [ ] Version list updates

### 1.13 API Endpoint Tests

```bash
# Test 1: Basic connectivity
curl "https://your-domain.com/pycamota/api/versions?debug=test"

# Test 2: Authentication
curl "https://your-domain.com/pycamota/api/versions?debug=auth"

# Test 3: Upload simulation
curl -X POST "https://your-domain.com/pycamota/api/versions?action=upload" \
     -H "Cookie: pycamota_admin=<session_id>" \
     -F "file=@PyRpiCamController-1.0.0.tar.gz" \
     -F "metadata={\"version\":\"1.0.0\",\"description\":\"Test version\"}"
```

## Security Considerations

### 1.14 Upload Security

- File type validation (only .tar.gz)
- File size limits (50MB default)
- Directory traversal protection
- Session timeout (configurable)
- CSRF protection
- HTTPS enforcement (configurable)
- Database input sanitization

## Next Steps

1. **Fix upload functionality** using this documentation
2. **Test manual file placement** in storage/versions/
3. **Test Pi-side OTA check** functionality
4. **Implement download API** for Pi devices
5. **Add version management** (delete, update status)
6. **Implement logging** for all operations