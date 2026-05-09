# Installer Updates & New Installation Setup

**Rule:** Any code change that affects new installations must be reflected in `tools/install-all-optimized.py`. Existing installations will not be affected unless an update script is provided separately.

## When to Update the Installer

### Checklist: Does Your Change Require Installer Update?

Before committing, ask yourself:

- ❓ Did I add a new Python package dependency?
- ❓ Did I add a new system package or service?
- ❓ Did I add a new file/directory that needs to exist on first install?
- ❓ Did I add a new configuration file or format?
- ❓ Did I add a new startup script or service file?
- ❓ Did I change permissions or ownership requirements?
- ❓ Did I add a new hardware configuration option?
- ❓ Did I add a new git hook or deployment setup?

**If ANY of these are YES**, update `tools/install-all-optimized.py`.

## Types of Installer Updates

### Type 1: New Python Package Dependency

**Trigger:** New `import statement` in existing or new module.

**Change:** Add package to installation batch.

```python
# In install-all-optimized.py, function: install_python_packages()

# Example: Adding weasyprint for PDF generation
packages_to_install = [
    "picamera2==0.3.12",
    "flask==2.3.2",
    "requests==2.31.0",
    "numpy==1.24.3",
    "weasyprint==59.0",  # NEW: For PDF generation in user guides
]
```

**Also update:**
- `tools/requirements.txt` with version pin
- `INSTALLATION.md` if package needs system dependencies (e.g., `libpango1.0-0` for weasyprint)
- `README.md` if affecting minimum system specs

**Related Files to Check:**
- `tests/requirements.txt` — Add test dependencies here too
- `backend/requirements.txt` — If backend uses the package
- `docs/requirements.txt` — If documentation generation affected

### Type 2: New System Package

**Trigger:** Code now requires system package (not installable via pip).

**Example:** Adding motion detection might need OpenCV system libs.

**Change:** Add to system package installation batch.

```python
# In setup_system_packages()

system_packages = {
    "core": [
        "build-essential",
        "git",
        "libatlas-base-dev",
        "libjasper-dev",
        "libharfbuzz0b",
        "libwebp6",
        "libatlas-base-dev",
        "postgresql",
        "postgresql-contrib",
        "libpq-dev",
        "libopenjp2-7",
        "libssl-dev",
        "libffi-dev",
        "libopencv-dev",  # NEW: For OpenCV system libraries
    ],
    "optional_streaming": [
        "ffmpeg",
        "vlc",
    ]
}
```

**Also update:**
- `INSTALLATION.md` with new system requirements section
- `.github/workflows/setup.sh` if using CI/CD

### Type 3: New Service File or Startup Script

**Trigger:** New `Services/*.service` or `Services/*.sh` file added.

**Change:** Copy and enable in installer.

```python
# In setup_services() or new function setup_new_service()

def setup_new_service():
    """Setup new service."""
    
    service_src = PROJECT_ROOT / "Services/new-service.service"
    service_dst = Path("/etc/systemd/system/new-service.service")
    
    log.log("INFO", "SERVICE", "Installing new-service.service...")
    subprocess.run(["sudo", "cp", str(service_src), str(service_dst)], check=True)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", "new-service.service"], check=True)
    
    log.log("SUCCESS", "SERVICE", "new-service.service installed")

# In main installation flow:
setup_services()
setup_new_service()  # Add this
```

**Also update:**
- Service file must have correct `User=`, `WorkingDirectory=`, `ExecStart=` paths
- Add entry to `TROUBLESHOOTING.md` with `systemctl status` commands
- Add entry to `INSTALLATION.md` listing all installed services
- Add entry to `README.md` if service is user-facing

### Type 4: New Shared Directory or Configuration File

**Trigger:** Code creates files in `/home/pi/shared/` or `/etc/camcontroller/`.

**Change:** Create directory, set permissions in installer.

```python
# In configure_directories() or new function setup_shared_structures()

def setup_shared_directories():
    """Create and configure shared directory structure."""
    
    dirs_to_create = [
        ("/home/pi/shared", "pi", "pi", "0755"),
        ("/home/pi/shared/images", "pi", "pi", "0755"),
        ("/home/pi/shared/logs", "pi", "pi", "0755"),
        ("/home/pi/shared/motion-events", "pi", "pi", "0755"),  # NEW
        ("/etc/camcontroller", "root", "root", "0755"),
        ("/etc/camcontroller/config", "pi", "root", "0750"),  # NEW
    ]
    
    for path, user, group, mode in dirs_to_create:
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        
        # Set ownership
        subprocess.run(["sudo", "chown", f"{user}:{group}", str(path_obj)], check=True)
        
        # Set permissions
        subprocess.run(["sudo", "chmod", mode, str(path_obj)], check=True)
        
        log.log("OK", "DIRS", f"Created {path} ({mode})")
```

**Also check:**
- If file/dir needs specific user/group ownership (usually `pi:pi` for shared, `root:root` for system)
- Permissions needed by service (readable, writable, executable?)
- See `FILE_PERMISSIONS.md` for SMB sharing permissions (usually `0777` dirs, `0666` files)

### Type 5: New Hardware Configuration Option

**Trigger:** `hwconfig.py` updated with new GPIO pin or device option.

**Change:** Update installer to ask user about new hardware.

```python
# In configure_hardware() or detect_hardware()

def detect_hardware():
    """Detect or prompt for hardware configuration."""
    
    config = {}
    
    # Existing
    config["Camera"] = detect_camera() or "PiCam3"
    
    # NEW: Prompt for motion sensor
    motion_enabled = input("Enable motion sensor? [y/N]: ").lower() == 'y'
    config["MotionSensor"] = motion_enabled
    
    if motion_enabled:
        motion_pin = input("Enter GPIO pin for motion sensor [17]: ").strip() or "17"
        config["MotionSensorPin"] = int(motion_pin)
    
    # Write to hwconfig
    hwconfig_path = PROJECT_ROOT / "CamController" / "hwconfig.py"
    write_hwconfig(hwconfig_path, config)
```

**Also update:**
- `INSTALLATION.md` with new hardware option
- `USER_GUIDE.md` if hardware is user-configurable
- `ARCHITECTURE.md` if adding new subsystem

### Type 6: New Startup or Initialization Script

**Trigger:** Added script that must run once or at service startup.

**Change:** Copy script, make executable, add to service or cron.

```python
# In setup_startup_scripts()

def setup_startup_scripts():
    """Copy and configure startup/initialization scripts."""
    
    scripts = [
        ("Services/self_heal_shared.sh", "/home/pi/PyRpiCamController/Services/self_heal_shared.sh"),
        ("Services/initialize_new_feature.sh", "/home/pi/PyRpiCamController/Services/initialize_new_feature.sh"),  # NEW
    ]
    
    for rel_path, target_path in scripts:
        src = PROJECT_ROOT / rel_path
        target = Path(target_path)
        
        if src.exists():
            subprocess.run(["sudo", "cp", str(src), str(target)], check=True)
            subprocess.run(["sudo", "chmod", "+x", str(target)], check=True)
            log.log("OK", "SCRIPTS", f"Made executable: {target}")

# In systemd service file (Services/camcontroller.service):
# ExecStartPre=/bin/bash /home/pi/PyRpiCamController/Services/initialize_new_feature.sh
```

**Make sure:**
- Script is executable (`chmod +x`)
- Script has proper shebang (`#!/bin/bash`)
- Script is idempotent (safe to run multiple times)
- Script logs output for debugging

### Type 7: New Web Interface or API Changes

**Trigger:** Changed routes, new API endpoints, or new template files.

**Change:** Update Flask app restart/reload in installer or docs.

```python
# In setup_web_service() or similar

def setup_web_service():
    """Setup Flask web service."""
    
    service_src = PROJECT_ROOT / "Services/camcontroller-web.service"
    service_dst = Path("/etc/systemd/system/camcontroller-web.service")
    
    log.log("INFO", "WEB", "Installing web service...")
    subprocess.run(["sudo", "cp", str(service_src), str(service_dst)], check=True)
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", "camcontroller-web.service"], check=True)
    
    log.log("SUCCESS", "WEB", "Web service installed")

# Also update:
# - WebGui/templates/ -- New templates must be included in package
# - WebGui/static/ -- CSS/JS changes included
# - USER_GUIDE.md -- Document new UI elements
```

## Installer Structure

Key sections in `tools/install-all-optimized.py`:

```python
def main():
    """Main installation flow."""
    
    # 1. Check prerequisites
    check_os()
    check_python_version()
    
    # 2. Install packages
    setup_system_packages()      # System packages (apt)
    setup_python_venv()          # Create Python virtualenv
    install_python_packages()    # Python packages (pip)
    
    # 3. Configure directories & files
    setup_shared_directories()   # Create /home/pi/shared
    setup_config_files()         # Copy default configs
    setup_startup_scripts()      # Add exit helper scripts
    
    # 4. Configure hardware
    configure_hardware()         # GPIO, camera selection, sensors
    
    # 5. Setup services
    setup_system_services()      # Enable/start systemd services
    setup_cron_jobs()            # If applicable
    
    # 6. Verify & test
    run_verification_tests()     # Smoke tests
    create_install_report()      # Log successful install
```

## Verification Checklist Before Commit

Before pushing code with installer changes:

- ✅ New package? Added to pip batch + `tools/requirements.txt`
- ✅ New system package? Added to apt batch + `INSTALLATION.md`
- ✅ New service? Enabled + started in `setup_services()`
- ✅ New script? Copied + made executable in installer
- ✅ New directory? Created + permissions set in installer
- ✅ New hardware option? Prompted for + documented in `INSTALLATION.md`
- ✅ Installation script tested? Ran full install on fresh Raspberry Pi (or using test_package.py)
- ✅ Documentation updated? `INSTALLATION.md`, `USER_GUIDE.md`, `TROUBLESHOOTING.md` as needed
- ✅ Backwards compatible? (Or noted as breaking change in commit message)
- ✅ Commit message references installer changes? (e.g., "feat: add motion detection - updated installer")

## Testing Installer Changes

### Quick Local Test

```bash
# Simulate install in a Python virtualenv
cd /tmp
mkdir test_install
cd test_install
cp -r /home/psk/Dropbox/dev/PyRpiCamController .
cd PyRpiCamController

# Run tests (doesn't need root)
cd tests
python -m pytest unit/test_installer_compatibility.py -v
```

### Full Install Test (Requires Raspberry Pi or VM)

```bash
# On target device (or after fresh OS install)
cd /tmp
curl -sL https://github.com/teddycool/PyRpiCamController/raw/main/tools/install-all-optimized.py | sudo python3

# Check results
sudo systemctl status camcontroller.service
sudo systemctl status camcontroller-web.service
```

### Validation Checklist After Install

```bash
# Services running?
sudo systemctl status camcontroller.service
sudo systemctl status camcontroller-web.service

# Python environment? 
/home/pi/PyRpiCamController/.venv/bin/python --version

# Shared directory structure?
ls -la /home/pi/shared/
ls -la /home/pi/shared/images/

# Permissions correct?
ls -la /home/pi/shared/images/ | grep "pi pi"

# Configuration files present?
ls -la /etc/camcontroller/ 2>/dev/null || echo "Not created"

# Logs accessible?
sudo tail -f /var/log/syslog | grep camcontroller
```

## Installer Anti-Patterns to Avoid

| Anti-Pattern | Why Avoid | Alternative |
|---|---|---|
| Manual step in installer | Error-prone, hard to automate | Automate with subprocess.run() |
| Hardcoded paths (no PROJECT_ROOT) | Breaks if installed elsewhere | Use Path() and PROJECT_ROOT variable |
| Missing error checking (check=False) | Silently fails, hard to debug | Always use check=True; log failures |
| Modifying user files directly | User customizations lost | Ask user to confirm; provide defaults |
| Installing as current user (no sudo) | Permissions wrong | Use sudo where system-wide install needed |
| No logging of installation | Can't debug failures later | Log all operations to shared/logs |
| Idempotent not required | Fails on re-run or upgrade | Ensure all operations can run multiple times safely |
