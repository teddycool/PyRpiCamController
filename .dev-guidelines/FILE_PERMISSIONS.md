# File Permissions & SMB Sharing Rules

**Principle:** File ownership and permissions are critical for SMB guest access. Incorrect permissions cause silent failures. Use atomic writes and startup healing to prevent data loss and permission issues.

## Hard-Learned Lessons

### Problem: SMB Guest Cannot Delete Files
**Symptom:** Guest user over SMB can read/write but cannot delete files.

**Root cause:** `camcontroller.service` runs as `root`, creating files with `root:root` ownership. Guest-mapped-to-pi user cannot delete root-owned files.

**Solution:**
1. Ensure all shared files are owned by `pi:pi`
2. Call `_ensure_smb_permissions()` after publishing files
3. Run a startup self-heal script via `ExecStartPre` in systemd service

### Problem: Power-Cut Corruption
**Symptom:** SMB share corrupted after unplanned power loss; file entries missing; filesystem inconsistent.

**Root cause:** Files written without `fsync`; writes buffered in filesystem cache, lost on power-off.

**Solution:**
1. Use atomic write pattern: `temp file → fsync → os.replace`
2. Never write directly to final path
3. Call `fsync()` on both file and parent directory

## Atomic Write Pattern

Use this pattern for all file operations:

```python
from pathlib import Path
import os
import tempfile

def write_file_atomically(target_path: Path, content: bytes | str):
    """Write file atomically to prevent corruption on power loss."""
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    # Write to temp file in same directory (ensure same filesystem)
    with tempfile.NamedTemporaryFile(
        dir=target_path.parent,
        delete=False,
        suffix='.tmp'
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())  # Force write to disk
    
    # Atomic rename
    tmp_path = Path(tmp.name)
    os.replace(tmp_path, target_path)
    
    # Sync parent directory
    parent_fd = os.open(target_path.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
```

## SMB Permissions Helper

After creating/updating files in the shared folder, call this:

```python
def _ensure_smb_permissions(shared_path: Path):
    """Ensure shared files are owned by pi:pi and have correct permissions."""
    import subprocess
    subprocess.run(
        ['sudo', 'chown', '-R', 'pi:pi', str(shared_path)],
        check=True
    )
    # Directories: 777 (full access)
    subprocess.run(
        ['sudo', 'find', str(shared_path), '-type', 'd', '-exec', 'chmod', '777', '{}', '+'],
        check=True
    )
    # Files: 666 (read/write, no execute)
    subprocess.run(
        ['sudo', 'find', str(shared_path), '-type', 'f', '-exec', 'chmod', '666', '{}', '+'],
        check=True
    )
```

**Location in codebase:** `CamController/Publishers/FilePublisher.py`

## Startup Self-Heal

Create `Services/self_heal_shared.sh`:

```bash
#!/bin/bash
# Restore /home/pi/shared ownership and permissions on every service start
# This prevents permission issues from power-cuts or manual interventions

SHARED_DIR="/home/pi/shared"

if [[ -d "$SHARED_DIR" ]]; then
    chown -R pi:pi "$SHARED_DIR" 2>/dev/null || true
    find "$SHARED_DIR" -type d -exec chmod 777 {} + 2>/dev/null || true
    find "$SHARED_DIR" -type f -exec chmod 666 {} + 2>/dev/null || true
fi
```

Hook into systemd service:

```ini
[Service]
# In camcontroller.service:
ExecStartPre=/bin/bash /home/pi/PyRpiCamController/Services/self_heal_shared.sh
ExecStart=/usr/bin/python3 /home/pi/PyRpiCamController/CamController/Main.py
```

Installer must mark script executable:
```bash
chmod +x /home/pi/PyRpiCamController/Services/self_heal_shared.sh
```

## SMB Configuration

Single sharable share in `Services/smb.conf`:

```ini
[shared]
    path = /home/pi/shared
    browseable = yes
    read only = no
    guest ok = yes
    force user = pi
    force group = pi
    create mask = 0666
    directory mask = 0777
```

**Do not create duplicate aliases** (e.g., avoid `[FileShare]` alongside `[shared]`).

## File Ownership: When to Change

| Scenario | Ownership | Command |
|----------|-----------|---------|
| Shared folder initialization | pi:pi | `chown pi:pi /home/pi/shared` |
| After service publishes files | pi:pi | `_ensure_smb_permissions()` in code OR startup script |
| Installer setup | pi:pi | Installer script (runs as sudo) |
| Manual cleanup | pi:pi | `sudo chown -R pi:pi /home/pi/shared` |

**Never** leave files as root:root in the shared folder.

## Testing Checklist

When modifying file handling code:
- ✅ Write atomic write tests (verify temp file → fsync → replace)
- ✅ Verify permissions after publish (`ls -l /home/pi/shared/`)
- ✅ Test as guest over SMB (read, write, delete)
- ✅ Simulate power-loss scenario (kill -9 while writing; check for corruption)
- ✅ Verify startup script runs (`systemctl status camcontroller.service` shows ExecStartPre success)

## Related Documentation

- `SMB_FILE_SHARING.md` — User-facing SMB setup and usage
- `TROUBLESHOOTING.md` — User troubleshooting for permission issues
- Files implementing these rules:
  - `CamController/Publishers/FilePublisher.py` — publish() with atomic writes
  - `Settings/settings_manager.py` — save_user_settings() with fsync
  - `Services/self_heal_shared.sh` — Startup permission repair
  - `tools/install-all-optimized.py` — Installer setup
