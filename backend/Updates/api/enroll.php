<?php
/**
 * Public API — consume one-time enrollment token and provision device API key.
 *
 * Route:
 *   POST /api/enroll
 *
 * Request JSON:
 * {
 *   "token": "plaintext enrollment token",
 *   "device_id": "cpu serial",
 *   "device_name": "optional local name",
 *   "notes": "optional"
 * }
 *
 * Response:
 * {
 *   "device_id": "...",
 *   "api_key": "...",
 *   "channel": "stable"
 * }
 */

require_once __DIR__ . '/../utils/helpers.php';

require_method('POST');

$body = json_body();

$token = trim((string)($body['token'] ?? ''));
$device_id = trim((string)($body['device_id'] ?? ''));
$device_name = trim((string)($body['device_name'] ?? ''));
$notes = trim((string)($body['notes'] ?? ''));

if (!$token || !$device_id) {
    json_error('token and device_id are required');
}

$token_hash = hash('sha256', $token);
$pdo = cam_db();

try {
    $stmt = $pdo->prepare("\n        SELECT *\n        FROM cam_enrollment_tokens\n        WHERE token_hash = ?\n          AND used_at IS NULL\n          AND expires_at > UTC_TIMESTAMP()\n        LIMIT 1\n    ");
    $stmt->execute([$token_hash]);
    $row = $stmt->fetch();
} catch (Exception $e) {
    json_error('Database error', 500);
}

if (!$row) {
    json_error('Invalid or expired token', 401);
}

$requested_device_id = strtolower($device_id);
$bound_device_id = strtolower((string)($row['device_id'] ?? ''));
if ($bound_device_id !== '' && $bound_device_id !== $requested_device_id) {
    json_error('Token is not valid for this device_id', 403);
}

$channel = (string)$row['channel'];
$final_name = $device_name !== '' ? $device_name : (string)($row['device_name'] ?? '');
$final_notes = $notes !== '' ? $notes : (string)($row['notes'] ?? '');

$api_key = generate_api_key();

try {
    $pdo->beginTransaction();

    // Ensure token still unused at write time (race safety).
    $update = $pdo->prepare("\n        UPDATE cam_enrollment_tokens\n        SET used_at = UTC_TIMESTAMP(), used_by_ip = ?\n        WHERE id = ? AND used_at IS NULL\n    ");
    $update->execute([
        $_SERVER['REMOTE_ADDR'] ?? null,
        (int)$row['id'],
    ]);

    if ($update->rowCount() !== 1) {
        $pdo->rollBack();
        json_error('Token already used', 409);
    }

    // Create or rotate device credentials.
    $find = $pdo->prepare('SELECT id FROM cam_devices WHERE device_id = ? LIMIT 1');
    $find->execute([$requested_device_id]);
    $existing = $find->fetch();

    if ($existing) {
        $pdo->prepare("\n            UPDATE cam_devices\n            SET api_key = ?,\n                name = COALESCE(NULLIF(?, ''), name),\n                channel = ?,\n                notes = COALESCE(NULLIF(?, ''), notes),\n                is_active = 1,\n                updated_at = NOW()\n            WHERE id = ?\n        ")->execute([
            $api_key,
            $final_name,
            $channel,
            $final_notes,
            (int)$existing['id'],
        ]);
    } else {
        $pdo->prepare("\n            INSERT INTO cam_devices (device_id, api_key, name, channel, notes, is_active)\n            VALUES (?, ?, ?, ?, ?, 1)\n        ")->execute([
            $requested_device_id,
            $api_key,
            $final_name ?: null,
            $channel,
            $final_notes ?: null,
        ]);
    }

    $pdo->commit();
} catch (Exception $e) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    json_error('Database error', 500);
}

json_ok([
    'device_id' => $requested_device_id,
    'api_key' => $api_key,
    'channel' => $channel,
], 201);
