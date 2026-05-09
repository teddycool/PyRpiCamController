# Code Quality & Testing Standards

**Principle:** All changes should be tested and verified to prevent regressions. Tests document expected behavior and catch breakage early.

## Before Every Commit

### 1. Run Unit Tests

```bash
cd /home/psk/Dropbox/dev/PyRpiCamController
.venv/bin/python -m pytest tests/unit/ -v --tb=short
```

**Expectations:**
- All tests pass (green)
- No new warnings introduced
- Coverage remains ≥80% for modified files

### 2. Run Integration Tests (if modifying affected subsystems)

```bash
.venv/bin/pytest tests/integration/ -v --tb=short
```

**Triggers:**
- Changes to Publisher code → test file share integration
- Changes to Settings → test settings load/save
- Changes to WiFi/Connectivity → test integration with Home Assistant

### 3. Lint & Type Check

```bash
# Unused imports and basic analysis
.venv/bin/pylint --disable=missing-docstring,too-many-instance-attributes CamController/ --exit-zero

# Type hints (if available)
.venv/bin/mypy CamController/ --ignore-missing-imports --exit-zero
```

**Expectations:**
- No critical errors introduced
- Type annotations on new public methods

### 4. Manual Smoke Tests (hardware available)

If touching Publisher, camera, or network code:

1. **Start service:** `sudo systemctl start camcontroller.service`
2. **Publish an image:** Use Web UI or API
3. **Verify SMB share:** Mount over SMB and check file appears
4. **Check file ownership:** `ls -l /home/pi/shared/<filename>` should show `pi:pi`
5. **Delete as guest:** SMB mount as guest, delete the file (should succeed)
6. **Check logs:** `sudo journalctl -u camcontroller.service -n 20`

## Code Standards

### Python Style

- **PEP 8 compliance** (use `black` for auto-formatting)
- **Line length:** 100 characters max
- **Imports:** Group stdlib, third-party, local (PEP 328)
- **Type hints:** On public methods and class attributes

Example:
```python
from pathlib import Path
from typing import Optional
import subprocess

class FilePublisher:
    def publish(self, image: Path, metadata: Optional[dict] = None) -> bool:
        """Publish image to shared folder atomically."""
        # Implementation...
```

### Error Handling

- **Catch specific exceptions** (not bare `except:`)
- **Log errors with context** before re-raising
- **Cleanup resources** in `finally` blocks or use context managers

Example:
```python
try:
    with open(temp_file, 'wb') as f:
        f.write(content)
        os.fsync(f.fileno())
except IOError as e:
    logger.error(f"Failed to write temp file {temp_file}: {e}")
    raise
finally:
    if temp_file.exists():
        temp_file.unlink()
```

### Documentation

- **Module docstrings:** Describe purpose and usage
- **Function docstrings:** One-liner + Args/Returns/Raises (Google style)
- **Comments:** Explain *why*, not *what* (code shows what)

Example:
```python
def _ensure_smb_permissions(path: Path) -> None:
    """Ensure files in shared path are writable by guest user over SMB.
    
    Args:
        path: Path to directory or file to fix permissions.
    
    Raises:
        PermissionError: If chown fails (needs sudo).
    """
    # We force ownership to pi:pi because guest-mapped-user
    # cannot delete root-owned files over SMB
    subprocess.run(['sudo', 'chown', '-R', 'pi:pi', str(path)], check=True)
```

## Testing Best Practices

### Unit Test Structure

```python
# tests/unit/test_file_publisher.py

import pytest
from pathlib import Path
from CamController.Publishers.FilePublisher import FilePublisher

class TestFilePublisher:
    """Test atomic writes and permission handling."""
    
    def test_publish_creates_file(self, tmp_path):
        """Verify publish() creates file in correct location."""
        pub = FilePublisher(tmp_path / 'shared')
        result = pub.publish(Path('test.jpg'), b'fake-jpeg')
        assert (tmp_path / 'shared' / 'test.jpg').exists()
    
    def test_publish_is_atomic(self, tmp_path):
        """Verify partial writes are not visible (atomicity)."""
        # Simulate write failure mid-way
        pub = FilePublisher(tmp_path / 'shared')
        with pytest.raises(IOError):
            pub.publish(Path('bad.jpg'), b'x' * 1000)  # Inject error
        # File should not exist or be complete
        assert not (tmp_path / 'shared' / 'bad.jpg').exists()
    
    def test_publish_permissions(self, tmp_path):
        """Verify files have pi:pi ownership (with mocking)."""
        pub = FilePublisher(tmp_path / 'shared')
        with patch('CamController.Publishers.FilePublisher._ensure_smb_permissions'):
            pub.publish(Path('test.jpg'), b'fake-jpeg')
            # Verify _ensure_smb_permissions was called
            _ensure_smb_permissions.assert_called_once()
```

### Integration Test Example

```python
# tests/integration/test_smb_publish.py

def test_publish_over_smb(mounted_smb_share):
    """Verify files published locally appear over SMB."""
    pub = FilePublisher(Path('/home/pi/shared'))
    pub.publish(Path('integration_test.jpg'), b'test-data')
    
    # Check file is visible over SMB
    smb_path = mounted_smb_share / 'integration_test.jpg'
    assert smb_path.exists()
    assert smb_path.read_bytes() == b'test-data'
    
    # Verify guest can delete (via SMB)
    # (This requires mounting as guest; see conftest.py fixtures)
```

## Continuous Integration Checklist

Use this before merging:

- ✅ All unit tests pass
- ✅ No new linting errors
- ✅ Documentation updated (see DOCUMENTATION_SYNC.md)
- ✅ Swedish docs or PDFs updated if applicable (see SWEDISH_TRANSLATIONS.md)
- ✅ Commit message is clear (see GIT_WORKFLOW.md)
- ✅ No secrets or passwords in code/comments
- ✅ No large binary files committed
- ✅ Related issues linked in commit message

## Common Pitfalls

| Pitfall | Protection |
|---------|-----------|
| Silent permission failures | Always test SMB guest access after file operations |
| Forgot to update docs | See DOCUMENTATION_SYNC.md checklist |
| Forgot Swedish translation | Check for `_swe` siblings before committing |
| Atomicity bugs | Use the atomic write pattern; test with simulated failures |
| Service doesn't heal after power-cut | Verify startup script runs; check `systemctl status` output |
