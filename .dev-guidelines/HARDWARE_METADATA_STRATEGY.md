# Hardware Metadata Strategy & Architecture

## Executive Summary

Add hardware metadata columns to the backend `cam_devices` table to track physical inventory. Enhance the enrollment flow to auto-detect and report hardware configuration. Keep IO pins and sensitive config **local-only**; report summary metadata to backend for admin visibility.

---

## 1. The Problem

Currently, the backend has minimal device data:
- `device_id`, `api_key`, `name`, `current_version`, `channel`, `last_seen`

Missing inventory visibility:
- What platform is each camera running? (Rpi3b+, Rpi4, Rpi5)
- How much RAM? (512MB, 1GB, 8GB)
- Which camera module? (PiCam2, PiCam3, PiCamHQ, WebCam)
- What accessory hardware? (Hailo HAT, custom expansions)
- Light/temperature sensors available?

**Use cases for this data:**
1. Admin dashboard: Quick hardware inventory drill-down
2. Release compatibility checks: "Release 1.0.7 requires Rpi4+ and PiCam3"
3. Health monitoring: "Devices with XYZ HAT report memory pressure"
4. Batch updates: "Deploy stable to all Rpi4 cameras only"
5. Troubleshooting: Admin can see device capability before support request

---

## 2. Proposed Backend Schema: cam_devices Extension

Add these columns to the `cam_devices` table:

```sql
ALTER TABLE cam_devices ADD COLUMN (
    -- Hardware identification
    platform            VARCHAR(32)     DEFAULT NULL,    -- 'Rpi3b+', 'Rpi4', 'Rpi5', etc.
    memory_gb           INT             DEFAULT NULL,    -- 1, 2, 4, 8 (gigabytes)
    camera_module       VARCHAR(32)     DEFAULT NULL,    -- 'PiCam2', 'PiCam3', 'PiCamHQ', 'WebCam'
    hat_installed       VARCHAR(64)     DEFAULT NULL,    -- 'Hailo', 'None', 'CustomHat', etc.
    
    -- Feature availability (boolean flags)
    lightbox_enabled    TINYINT(1)      DEFAULT 0,       -- Has light control (GPIO PWM)
    has_ds18b20        TINYINT(1)      DEFAULT 0,       -- Has temperature sensor (1-wire)
    has_display        TINYINT(1)      DEFAULT 0,       -- Has LED display (NeoPixel)
    
    -- Metadata
    hardware_info_reported_at  DATETIME  DEFAULT NULL,  -- Last update to hardware fields
    hardware_info_source       VARCHAR(32) DEFAULT NULL, -- 'enrollment', 'daemon-refresh', 'manual'
    
    INDEX idx_cam_devices_platform_cam (platform, camera_module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Rationale:**
- `platform`, `camera_module`, `hat_installed`: Direct inventory (picklists, not free text, for filtering/sorting)
- `memory_gb`: Numeric for range queries ("show all cameras < 2GB RAM")
- `lightbox_enabled`, `has_ds18b20`, `has_display`: Boolean flags (efficient, searchable)
- `hardware_info_reported_at`: Audit trail (when was this data collected?)
- `hardware_info_source`: Track whether data came from auto-enrollment or manual refresh

---

## 3. Pi-Side Hardware Detection

Create a **hardware manifest** that is read early in the provisioning/enrollment flow.

### 3.1 Hardware Sources (Priority Order)

1. **hwconfig.py** (authoritative, fixed at installation):
   - `"RpiBoard"`: Platform identifier
   - `"CamChip"`: Camera module
   - `"LightBox"`: Boolean flag
   - `"Io"`: Nested GPIO config with `ds18b20pin`, `displaycontrolgpio`

2. **Runtime detection** (`/proc/meminfo`, `/proc/cpuinfo`):
   - Total RAM
   - CPU model (to cross-check with RpiBoard if needed)

3. **User input** (during enrollment or via web UI):
   - HAT name (if not auto-detectable)
   - Custom hardware notes

### 3.2 Hardware Detection Function (Pi-side)

```python
# Pseudo-code for new function in secure_enroll_device.py or shared module

def detect_hardware_info(host: str, ssh_user: str, ssh_port: int) -> Dict[str, Any]:
    """
    SSH to Pi and gather hardware metadata.
    
    Returns dict with keys:
    - platform (str): 'Rpi3b+', 'Rpi4', 'Rpi5', etc.
    - memory_gb (int): Total RAM in gigabytes
    - camera_module (str): 'PiCam2', 'PiCam3', 'PiCamHQ', 'WebCam'
    - lightbox_enabled (bool): True if hwconfig["LightBox"] == True
    - has_ds18b20 (bool): True if ds18b20pin is configured
    - has_display (bool): True if displaycontrolgpio is configured
    - hat_installed (str or None): 'Hailo', 'None', or user-provided name
    """
    
    # Step 1: Read hwconfig from Pi
    hwconfig_py = run_ssh(host, ssh_user, ssh_port, "cat ~/PyRpiCamController/CamController/hwconfig.py")
    # Parse Python dict: Extract "RpiBoard", "CamChip", "LightBox", "Io"
    
    # Step 2: Auto-detect RAM from /proc/meminfo
    meminfo = run_ssh(host, ssh_user, ssh_port, "grep MemTotal /proc/meminfo | awk '{print $2}'")
    memory_kb = int(meminfo.stdout.strip())
    memory_gb = max(1, memory_kb // (1024 ** 2))  # Round to nearest GB, min 1GB
    
    # Step 3: Check for optional hardware via hwconfig pins
    has_ds18b20 = ds18b20_pin is not None in hwconfig["Io"]
    has_display = displaycontrolgpio is not None in hwconfig["Io"]
    
    # Step 4: Ask user about HAT (or skip if --hat-name provided)
    hat = user_input("HAT installed (Hailo/None/Custom name)? [None]") or "None"
    
    return {
        "platform": hwconfig["RpiBoard"],
        "memory_gb": memory_gb,
        "camera_module": hwconfig["CamChip"],
        "lightbox_enabled": hwconfig["LightBox"],
        "has_ds18b20": has_ds18b20,
        "has_display": has_display,
        "hat_installed": hat,
    }
```

---

## 4. New Backend Endpoint: /api/hardware_info

Create a new authenticated endpoint for hardware metadata updates.

### 4.1 Endpoint Specification

**POST** `/api/hardware_info`

**Authentication:** Device API key (same as OTA check requests)

**Request body:**
```json
{
  "device_id": "0x12345678abcdef",
  "api_key": "sha256hex...",
  "hardware": {
    "platform": "Rpi4",
    "memory_gb": 4,
    "camera_module": "PiCam3",
    "lightbox_enabled": true,
    "has_ds18b20": true,
    "has_display": false,
    "hat_installed": "Hailo"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Hardware metadata updated",
  "device_id": "0x12345678abcdef",
  "updated_at": "2026-07-28T10:30:45Z"
}
```

**Response (401 Unauthorized):**
```json
{
  "success": false,
  "error": "Invalid device_id or api_key"
}
```

### 4.2 Backend PHP Implementation (Note-level pseudocode)

```php
<?php
// hardware_info.php

// 1. Extract device_id and api_key from request
$device_id = $_POST['device_id'] ?? null;
$api_key = $_POST['api_key'] ?? null;
$hardware_json = $_POST['hardware'] ?? '{}';

// 2. Validate device_id + api_key against cam_devices table
$stmt = $cam_db->prepare("
  SELECT id FROM cam_devices 
  WHERE device_id = ? AND api_key = ? AND is_active = 1
");
$stmt->execute([$device_id, $api_key]);
$device = $stmt->fetch();

if (!$device) {
  http_response_code(401);
  echo json_encode(['success' => false, 'error' => 'Invalid credentials']);
  exit;
}

// 3. Parse and validate hardware JSON
$hw = json_decode($hardware_json, true);
if (!is_array($hw)) {
  http_response_code(400);
  echo json_encode(['success' => false, 'error' => 'Invalid hardware JSON']);
  exit;
}

// 4. Update cam_devices with hardware info
$update = $cam_db->prepare("
  UPDATE cam_devices SET
    platform = ?,
    memory_gb = ?,
    camera_module = ?,
    lightbox_enabled = ?,
    has_ds18b20 = ?,
    has_display = ?,
    hat_installed = ?,
    hardware_info_reported_at = UTC_TIMESTAMP(),
    hardware_info_source = ?
  WHERE id = ?
");

$update->execute([
  $hw['platform'] ?? null,
  $hw['memory_gb'] ?? null,
  $hw['camera_module'] ?? null,
  $hw['lightbox_enabled'] ? 1 : 0,
  $hw['has_ds18b20'] ? 1 : 0,
  $hw['has_display'] ? 1 : 0,
  $hw['hat_installed'] ?? null,
  'enrollment',  // or 'daemon-refresh' for periodic updates
  $device['id']
]);

// 5. Return success
http_response_code(200);
echo json_encode([
  'success' => true,
  'message' => 'Hardware metadata updated',
  'device_id' => $device_id,
  'updated_at' => gmdate('Y-m-d\TH:i:s\Z')
]);
?>
```

---

## 5. Enrollment Flow Enhancement

Modify `secure_enroll_device.py` to call the new hardware info endpoint.

### Current Flow:
1. SSH → read CPU serial
2. Admin login → create token
3. Consume token → get API key
4. Push OTA settings to Pi
5. Restart daemon

### Enhanced Flow:
1. SSH → read CPU serial + **auto-detect hardware**
2. Admin login → create token
3. Consume token → get API key + **send hardware info to backend**
4. Push OTA settings to Pi
5. Restart daemon

**Code outline:**
```python
def enroll_device(host, ssh_user, ssh_port, device_name, location, channel, 
                  update_group, test_device, hat_name=None):
    """Enhanced enroll with hardware detection."""
    
    # 1. Get CPU serial
    cpu_serial = get_remote_cpu_serial(host, ssh_user, ssh_port)
    
    # 2. **NEW: Detect hardware**
    hardware = detect_hardware_info(host, ssh_user, ssh_port)
    if hat_name:
        hardware['hat_installed'] = hat_name
    
    # 3. Login and create token (existing)
    session = admin_login(backend_config)
    token = create_enrollment_token(session, cpu_serial, device_name, channel)
    
    # 4. Consume token + **send hardware inside payload**
    api_key = consume_enrollment_token(
        session,
        cpu_serial,
        device_name,
        channel,
        hardware=hardware  # **NEW parameter**
    )
    
    # 5. Push OTA settings (existing)
    push_settings_to_pi(host, ssh_user, ssh_port, api_key, ...)
    
    # 6. Restart daemon (existing)
    restart_remote_services(host, ssh_user, ssh_port)
```

---

## 6. IO & Lightbox Handling Strategy

### 6.1 What Gets Sent to Backend (Summary Only)

✅ **DO send:**
- `lightbox_enabled` (boolean: has PWM light control)
- `has_ds18b20` (boolean: has temperature sensor)
- `has_display` (boolean: has LED display)

❌ **DO NOT send:**
- GPIO pin numbers themselves
- Specific PWM channel assignments
- Kernel module configuration
- Device tree overlay details
- Any other GPIO/kernel-level details

**Rationale:** GPIO pin numbers and kernel config are:
1. **Security risk**: Never expose GPIO pinout to backend
2. **Not needed** for OTA, compatibility checks, or admin dashboard
3. **Implementation detail**: Backend doesn't control GPIO, Pi does

### 6.2 IO Configuration Stays Local

```python
# hwconfig.py (NEVER sent to backend)
hwconfig1 = {
    "RpiBoard": "Rpi4",
    "CamChip": "PiCam3",
    "LightBox": True,  ← This boolean IS reported
    "Io": {            ← This section STAYS local
        "lightcontrolgpio": 12,        ← NOT sent
        "displaycontrolgpio": 18,      ← NOT sent
        "displaysize": 1,              ← NOT sent
        "ds18b20pin": 22,              ← NOT sent
    },
}
```

Reported to backend:
```json
{
  "lightbox_enabled": true,          ← Derived from LightBox flag
  "has_ds18b20": true,               ← Derived from ds18b20pin != None
  "has_display": true,               ← Derived from displaycontrolgpio != None
}
```

### 6.3 Lightbox Behavior

On the Pi, LightBox behavior is **unchanged**:
- hwconfig defines `"LightBox": True/False`
- If `True`, MainLoop initializes Light.Light() with `hwconfig["Io"]["lightcontrolgpio"]`
- Light() handles PWM backend selection (pigpio → lgpio fallback)

On the backend (new):
- Admin can see which cameras have light capability
- Could use for feature-dependent UI (show "light control" widget only if `lightbox_enabled = 1`)
- Could implement release notes like: "Light improvements in 1.0.8 benefit devices with lightbox_enabled = 1"

---

## 7. Installer & Provisioning Tool Updates

### 7.1 install-all-optimized.py Enhancements

Add optional hardware inventory collection during fresh install:

```python
def collect_hardware_info(interactive=True) -> Dict[str, Any]:
    """Gather hardware metadata for this installation."""
    
    # Auto-detect from system
    platform = detect_rpi_model()  # Rpi3b+, Rpi4, Rpi5, etc.
    memory = get_system_memory_gb()
    
    if interactive:
        # Ask user
        camera = input("Camera module (PiCam2/PiCam3/PiCamHQ/WebCam)? [PiCam3]: ").strip() or "PiCam3"
        has_light = input("Lightbox / light control? [y/N]: ").lower() == 'y'
        hat = input("HAT name (Hailo/None)? [None]: ").strip() or "None"
    else:
        # Defaults from hwconfig
        camera = hwconfig.get("CamChip")
        has_light = hwconfig.get("LightBox", False)
        hat = "None"
    
    return {
        "platform": platform,
        "memory_gb": memory,
        "camera_module": camera,
        "lightbox_enabled": has_light,
        "hat_installed": hat,
    }

def main():
    # ... existing setup code ...
    
    # NEW: Collect hardware metadata
    hardware_info = collect_hardware_info()
    save_hardware_metadata("/etc/camcontroller/hwinfo.json", hardware_info)
```

### 7.2 Hardware Changes (Rare, Explicit)

If hardware changes after enrollment (e.g., user adds a HAT or swaps camera module), it is **not** automatically refreshed on the backend. This is intentional:

**Rationale:**
- Hardware configuration is typically **static** once installed
- Explicit > implicit — if user changes hardware, they should explicitly update the backend
- No unnecessary daemon overhead for rarely-changing data

**How to update if hardware changes:**
- Option A: Re-run `secure_enroll_device.py` with `--force-hardware-refresh` flag
- Option B: Manual admin dashboard button "Refresh Hardware Info" (triggers Pi to POST to `/api/hardware_info`)
- Option C: Direct update via admin backend UI (edit fields directly)

**Note:** For v1.0, enrollment-time capture is sufficient. Re-run enrollment tool if hardware config changes.

---

## 8. Web UI & Admin Dashboard Impact

### 8.1 Device List View Enhancement

Current: Device name, last version, last seen
Enhanced: New columns/filters available:
- Platform filter: "Show Rpi4 devices"
- Camera filter: "Show PiCam3+ only"
- Features: "Show cameras with light control"
- Memory: "Show devices > 2GB RAM"

### 8.2 Device Detail View

Show hardware metadata card:
```
HARDWARE
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Platform:     Rpi4 4GB
Camera:       PiCam3
HAT:          Hailo-8L
Features:     Light 🔆  | DS18B20 🌡 | Display 📺
Last Updated: 2026-07-28 10:30:45 UTC
```

### 8.3 Compatibility Check

Show warnings for devices that don't meet release requirements:
```
⚠ Release v1.1.0 requires:
  - Rpi4+ (Your device: Rpi3b+ ❌)
  - 2GB+ RAM (Your device: 1GB ❌)
  
CANNOT APPLY: Hardware insufficient
```

---

## 9. Implementation Timeline

### Phase 1: Backend (Ready to Deploy)
- Add schema columns to `cam_devices`
- Implement `/api/hardware_info` endpoint
- Add `.htaccess` routing
- **No breaking changes** (all new columns nullable)

### Phase 2: Dev Tools (Next Iteration)
- Enhance `secure_enroll_device.py` with `detect_hardware_info()`
- Call hardware_info endpoint after token consumption
- Support `--hat-name` CLI flag

### Phase 3: Admin UI (Optional follow-up)
- Add hardware filters to device list
- Show hardware detail card
- Implement compatibility checking
- Optional: Manual "Refresh Hardware" button for devices that changed hardware

---

## 10. Security & Privacy Considerations

✅ **Safe to collect:**
- Platform (Rpi3b+, Rpi4, etc.) — just marketing name
- Memory (1GB, 4GB, etc.) — system resource
- Camera module (PiCam3, etc.) — device model
- HAT name (Hailo, None) — external accessory
- Feature flags (has_light, has_ds18b20) — software mode

❌ **Never collect:**
- GPIO pin assignments (security: exposes hardware pinout)
- MAC address (privacy: PII in some contexts)
- Full /proc/cpuinfo (privacy: leaks CPU model details)
- Device tree blob or boot config (security: kernel config)

---

## 11. Backward Compatibility

All new columns are **nullable** with **default NULL**. Existing devices continue to work:
- Old installations won't have hardware data → fields remain NULL
- Admin dashboard handles NULL gracefully (show "Not reported" or "Unknown")
- No breaking changes to `/api/enroll` flow
- Existing `enroll` endpoint can optionally skip hardware if not provided

---

## Summary: The Three-Tier Model

| Tier | Where | What | Mutable |
|------|-------|------|---------|
| **Device** (Pi) | `hwconfig.py` | Full GPIO config, kernel setup, all IO details | No (fixed at install) |
| **Device** (Pi) | `user_settings.json` | OTA settings, app config | Yes (web UI) |
| **Backend** | `cam_devices` | Hardware summary (platform, RAM, camera, hat, feature flags) | Yes (via hardware_info endpoint or admin refresh) |

**Flow:** hwconfig.py → auto-detect on enrollment → report to backend → admin dashboard

This keeps **security tight**, **inventory visible**, and **flexibility high**.

---

## Recommended Next Steps

1. ✅ Review this strategy (you are here)
2. ⏭ Add schema columns to `ota_schema_v2.sql`
3. ⏭ Implement `/api/hardware_info` endpoint
4. ⏭ Enhance `secure_enroll_device.py` with hardware detection
5. ⏭ Test with first fresh Pi enrollment
6. ⏭ (Optional) Add admin UI filters
7. ⏭ (Optional) Periodic daemon refresh

