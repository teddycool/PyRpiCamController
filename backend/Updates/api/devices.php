<?php
/**
 * Admin API — device management.
 *
 * Routes (all require active admin session):
 *   GET    /api/devices.php           — list all devices
 *   POST   /api/devices.php           — register new device
 *   PUT    /api/devices.php?id=<n>    — update device fields
 *   DELETE /api/devices.php?id=<n>    — delete device
 */

require_once __DIR__ . '/../utils/helpers.php';

require_admin_api();

$method = $_SERVER['REQUEST_METHOD'];
$id     = isset($_GET['id']) ? (int) $_GET['id'] : null;
$pdo    = cam_db();

// ---------------------------------------------------------------------------
// GET — list devices
// ---------------------------------------------------------------------------
if ($method === 'GET') {
    $rows = $pdo->query("
        SELECT id, device_id, name, current_version, channel, is_active,
               last_seen, last_ip, notes, created_at
        FROM   cam_devices
        ORDER  BY name, device_id
    ")->fetchAll();

    json_ok($rows);
}

// ---------------------------------------------------------------------------
// POST — register new device
// ---------------------------------------------------------------------------
if ($method === 'POST') {
    $body      = json_body();
    $device_id = trim($body['device_id'] ?? '');
    $name      = trim($body['name']      ?? '');
    $channel   = trim($body['channel']   ?? 'stable');
    $notes     = trim($body['notes']     ?? '');

    if (!$device_id) {
        json_error('device_id is required');
    }
    if (!in_array($channel, ['stable', 'testing', 'beta'], true)) {
        json_error('channel must be stable, testing, or beta');
    }

    $api_key = generate_api_key();

    try {
        $stmt = $pdo->prepare("
            INSERT INTO cam_devices (device_id, api_key, name, channel, notes)
            VALUES (?, ?, ?, ?, ?)
        ");
        $stmt->execute([$device_id, $api_key, $name ?: null, $channel, $notes ?: null]);
        $new_id = (int) $pdo->lastInsertId();
    } catch (PDOException $e) {
        if ($e->getCode() === '23000') {
            json_error('device_id already registered', 409);
        }
        json_error('Database error', 500);
    }

    json_ok([
        'id'        => $new_id,
        'device_id' => $device_id,
        'api_key'   => $api_key,   // shown only on creation
        'channel'   => $channel,
    ], 201);
}

// ---------------------------------------------------------------------------
// PUT — update device
// ---------------------------------------------------------------------------
if ($method === 'PUT') {
    if (!$id) {
        json_error('id is required');
    }

    $body    = json_body();
    $fields  = [];
    $params  = [];

    $allowed = ['name', 'channel', 'notes', 'is_active'];
    foreach ($allowed as $f) {
        if (array_key_exists($f, $body)) {
            $fields[] = "$f = ?";
            $params[] = $f === 'channel' ? trim($body[$f]) : $body[$f];
        }
    }
    if (!$fields) {
        json_error('No updatable fields provided');
    }

    $params[] = $id;
    $pdo->prepare('UPDATE cam_devices SET ' . implode(', ', $fields) . ' WHERE id = ?')
        ->execute($params);

    json_ok(['updated' => true]);
}

// ---------------------------------------------------------------------------
// DELETE — remove device
// ---------------------------------------------------------------------------
if ($method === 'DELETE') {
    if (!$id) {
        json_error('id is required');
    }

    $pdo->prepare('DELETE FROM cam_devices WHERE id = ?')->execute([$id]);
    json_ok(['deleted' => true]);
}

json_error('Method not allowed', 405);
