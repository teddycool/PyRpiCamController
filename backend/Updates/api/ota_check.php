<?php
/**
 * GET /api/ota/check
 *
 * Query params:
 *   cpu_id          (string) device hardware serial
 *   current_version (string) e.g. "1.0.2"
 *   api_key         (string) device secret
 *
 * Response (update available):
 * {
 *   "update_available": true,
 *   "version":          "1.0.3",
 *   "download_url":     "https://www.sensorwebben.se/pycamota/releases/PyRpiCamController-1.0.3.tar.gz",
 *   "checksum":         "<sha256 hex>",
 *   "filesize":         1234567,
 *   "release_notes":    "..."
 * }
 *
 * Response (no update):
 * { "update_available": false }
 */

require_once __DIR__ . '/../utils/helpers.php';

require_method('GET');

// Authenticate device (also updates last_seen)
$device = authenticate_device();

// Resolve current version from query string
$current_version = trim($_GET['current_version'] ?? '');

// Update device's stored version if it has changed
if ($current_version && $current_version !== $device['current_version']) {
    try {
        cam_db()->prepare('UPDATE cam_devices SET current_version = ? WHERE id = ?')
                ->execute([$current_version, $device['id']]);
    } catch (Exception $e) {
        // Non-fatal
    }
}

// Find the best available release for this device's channel
// Rules:
//   - status = 'stable'  for the device's channel
//   - version > current_version  (semantic comparison via ORDER BY, relying on SEMVER-safe strings)
//   - min_version IS NULL  OR  current_version >= min_version
try {
    $pdo  = cam_db();
    $stmt = $pdo->prepare("
        SELECT *
        FROM   cam_releases
        WHERE  channel = ?
          AND  status  = 'stable'
        ORDER BY created_at DESC
        LIMIT 1
    ");
    $stmt->execute([$device['channel']]);
    $release = $stmt->fetch();
} catch (Exception $e) {
    json_error('Database error', 500);
}

// Log the check event regardless of outcome
try {
    $pdo->prepare("
        INSERT INTO cam_ota_logs
            (device_id, event_type, from_version, to_version, release_id, success, message, client_ip)
        VALUES (?, 'check', ?, ?, ?, 1, ?, ?)
    ")->execute([
        $device['device_id'],
        $current_version ?: null,
        $release ? $release['version'] : null,
        $release ? $release['id']      : null,
        $release ? 'update available'  : 'no update available',
        $_SERVER['REMOTE_ADDR'] ?? null,
    ]);
} catch (Exception $e) {
    // Non-fatal — don't fail the check because logging failed
}

if (!$release) {
    json_ok(['update_available' => false]);
}

// Decide if the found release is actually newer
if (!$current_version || version_compare($release['version'], $current_version, '>')) {
    // Check min_version constraint
    if ($release['min_version'] && version_compare($current_version, $release['min_version'], '<')) {
        // Device is too old to receive this release
        json_ok(['update_available' => false]);
    }

    json_ok([
        'update_available' => true,
        'version'          => $release['version'],
        'download_url'     => CAM_RELEASES_URL . '/' . $release['filename'],
        'checksum'         => $release['checksum_sha256'],
        'filesize'         => (int) $release['filesize'],
        'release_notes'    => $release['release_notes'],
    ]);
}

json_ok(['update_available' => false]);
