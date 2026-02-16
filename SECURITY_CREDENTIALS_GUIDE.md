# Security Guide for OTA Credentials

## Overview
This guide explains how to securely manage OTA (Over-The-Air) admin credentials for PyRpiCamController device registration and management.

## Security Incident Resolution
If credentials were accidentally committed to version control:

1. **Immediate Action**: Change the compromised credentials on your OTA server
2. **Remove from Git**: The credentials file has been removed from tracking
3. **Update .gitignore**: Added `tools/ota_credentials.txt` to prevent future commits
4. **Use Template**: Configure using `tools/ota_credentials.txt.template`

## Secure Credential Setup

### For New Deployments
1. Copy the template:
   ```bash
   cp tools/ota_credentials.txt.template tools/ota_credentials.txt
   ```

2. Edit `tools/ota_credentials.txt` with your actual credentials:
   ```
   ADMIN_USERNAME=your_admin_username
   ADMIN_PASSWORD=your_secure_admin_password
   OTA_SERVER_URL=https://your-ota-server.com/api
   ```

3. Set secure file permissions:
   ```bash
   chmod 600 tools/ota_credentials.txt
   ```

### For Production Environments
- Use strong, unique passwords (minimum 16 characters)
- Consider using environment variables instead of files
- Implement credential rotation policies
- Restrict admin account permissions to minimum required
- Use separate authentication for production vs development

### Environment Variables (Recommended)
Instead of files, you can use environment variables:
```bash
export ADMIN_USERNAME="your_admin_username"
export ADMIN_PASSWORD="your_secure_password"
export OTA_SERVER_URL="https://your-ota-server.com/api"
```

Update your scripts to check for environment variables first:
```python
import os

username = os.getenv('ADMIN_USERNAME') or get_from_credentials_file()
password = os.getenv('ADMIN_PASSWORD') or get_from_credentials_file()
```

## Best Practices
1. **Never commit credentials to version control**
2. **Use different credentials for development/staging/production**
3. **Implement credential rotation**
4. **Monitor access logs**
5. **Use strong, unique passwords**
6. **Restrict file permissions (chmod 600)**
7. **Consider using a secrets management system**

## Emergency Response
If credentials are compromised:
1. Immediately change passwords on the OTA server
2. Review server access logs for unauthorized activity
3. Generate new strong credentials
4. Update all devices with new registration endpoints if needed
5. Document the incident and review security procedures

## Files Involved
- `tools/ota_credentials.txt.template` - Safe template (can be committed)
- `tools/ota_credentials.txt` - Actual credentials (ignored by git)
- `.gitignore` - Contains exclusion for credentials file