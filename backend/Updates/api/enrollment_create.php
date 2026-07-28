<?php
/**
 * Admin API — create one-time enrollment token.
 *
 * Route:
 *   POST /api/enrollment/create
 *
 * Request JSON:
 * {
 *   "device_id": "optional-known-cpu-id",
 *   "device_name": "Kitchen Cam",
 *   "channel": "stable|testing|beta",
 *   "notes": "optional",
 *   "ttl_minutes": 10
 * }
 *
 * Response:
 * {
 *   "token": "plaintext token shown once",
 *   "expires_at": "UTC datetime",
 *   "channel": "stable"
 * }
 */

require_once __DIR__ . '/../utils/helpers.php';

require_admin_api();
require_method('POST');

$body = json_body();

$device_id = trim((string)($body['device_id'] ?? ''));
$device_name = trim((string)($body['device_name'] ?? ''));
$channel = trim((string)($body['channel'] ?? 'stable'));
$notes = trim((string)($body['notes'] ?? ''));
$ttl = (int)($body['ttl_minutes'] ?? 10);

if (!in_array($channel, ['stable', 'testing', 'beta'], true)) {
    json_error('channel must be stable, testing, or beta');
}

if ($ttl < 1 || $ttl > 120) {
    json_error('ttl_minutes must be between 1 and 120');
}

$token = bin2hex(random_bytes(24));
$hash = hash('sha256', $token);
$expires_at = gmdate('Y-m-d H:i:s', time() + ($ttl * 60));

$admin_id = null;
if (session_status() === PHP_SESSION_NONE) {
    session_name(CAM_SESSION_NAME);
    session_start();
}
if (!empty($_SESSION['admin_id'])) {
    $admin_id = (int)$_SESSION['admin_id'];
}

try {
    cam_db()->prepare("\n        INSERT INTO cam_enrollment_tokens\n            (token_hash, device_id, device_name, channel, notes, expires_at, created_by)\n        VALUES (?, ?, ?, ?, ?, ?, ?)\n    ")->execute([
        $hash,
        $device_id ?: null,
        $device_name ?: null,
        $channel,
        $notes ?: null,
        $expires_at,
        $admin_id,
    ]);
} catch (Exception $e) {
    json_error('Database error', 500);
}

json_ok([
    'token' => $token,
    'expires_at' => $expires_at,
    'channel' => $channel,
], 201);
