<?php
/**
 * POST /api/ota/report
 *
 * JSON body:
 * {
 *   "cpu_id":        "...",
 *   "api_key":       "...",
 *   "status":        "install_ok" | "install_fail" | "rollback" | "download_start",
 *   "version":       "1.0.3",          -- the version being installed
 *   "timestamp":     "2026-07-27T...", -- ISO 8601 (informational, we use server time)
 *   "error_message": "..."             -- optional, present on failure
 * }
 *
 * Response:
 * { "received": true }
 */

require_once __DIR__ . '/../utils/helpers.php';

require_method('POST');

$body = json_body();

// Merge body params into $_GET so authenticate_device() can find them
$_GET['cpu_id']  = $body['cpu_id']  ?? null;
$_GET['api_key'] = $body['api_key'] ?? null;

$device = authenticate_device();

$status  = $body['status']        ?? null;
$version = $body['version']       ?? null;
$error   = $body['error_message'] ?? null;

$allowed_statuses = ['check', 'download_start', 'install_ok', 'install_fail', 'rollback'];
if (!$status || !in_array($status, $allowed_statuses, true)) {
    json_error('Invalid or missing status. Allowed: ' . implode(', ', $allowed_statuses));
}

// Determine success flag
$success = match ($status) {
    'install_ok'      => 1,
    'install_fail'    => 0,
    'rollback'        => 0,
    'download_start'  => null,  // informational
    'check'           => null,
    default           => null,
};

// Look up the release (optional — best effort)
$release_id   = null;
$from_version = $device['current_version'];
try {
    if ($version) {
        $stmt = cam_db()->prepare(
            "SELECT id FROM cam_releases WHERE version = ? LIMIT 1"
        );
        $stmt->execute([$version]);
        $row = $stmt->fetch();
        $release_id = $row['id'] ?? null;
    }
} catch (Exception $e) {
    // Non-fatal
}

// Write log entry
try {
    cam_db()->prepare("
        INSERT INTO cam_ota_logs
            (device_id, event_type, from_version, to_version, release_id, success, message, client_ip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ")->execute([
        $device['device_id'],
        $status,
        $from_version,
        $version,
        $release_id,
        $success,
        $error,
        $_SERVER['REMOTE_ADDR'] ?? null,
    ]);
} catch (Exception $e) {
    json_error('Database error', 500);
}

// On successful install, update the device's stored version
if ($status === 'install_ok' && $version) {
    try {
        cam_db()->prepare('UPDATE cam_devices SET current_version = ? WHERE id = ?')
                ->execute([$version, $device['id']]);
    } catch (Exception $e) {
        // Non-fatal
    }
}

json_ok(['received' => true]);
