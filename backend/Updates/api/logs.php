<?php
/**
 * Admin API — OTA log viewer.
 *
 * GET /api/logs.php
 *   ?limit=50         (default 50, max 200)
 *   ?offset=0
 *   ?device_id=<str>  (optional filter)
 *   ?event_type=<str> (optional filter)
 */

require_once __DIR__ . '/../utils/helpers.php';

require_admin_api();
require_method('GET');

$limit  = min((int) ($_GET['limit']  ?? 50), 200);
$offset = max((int) ($_GET['offset'] ?? 0),  0);

$where  = [];
$params = [];

if (!empty($_GET['device_id'])) {
    $where[]  = 'device_id LIKE ?';
    $params[] = '%' . $_GET['device_id'] . '%';
}
if (!empty($_GET['event_type'])) {
    $where[]  = 'event_type = ?';
    $params[] = $_GET['event_type'];
}

$whereSQL = $where ? 'WHERE ' . implode(' AND ', $where) : '';

try {
    $pdo = cam_db();

    $countStmt = $pdo->prepare("SELECT COUNT(*) FROM cam_ota_logs $whereSQL");
    $countStmt->execute($params);
    $total = (int) $countStmt->fetchColumn();

    $rowStmt = $pdo->prepare("
        SELECT id, device_id, event_type, from_version, to_version,
               success, message, client_ip, created_at
        FROM   cam_ota_logs
        $whereSQL
        ORDER  BY id DESC
        LIMIT  ? OFFSET ?
    ");
    $rowStmt->execute(array_merge($params, [$limit, $offset]));
    $rows = $rowStmt->fetchAll();
    
    // PHP 8.3: Ensure all string values are valid UTF-8 for JSON encoding
    $rows = array_map(function($row) {
        foreach ($row as $key => $value) {
            if (is_string($value) && !mb_check_encoding($value, 'UTF-8')) {
                $row[$key] = mb_convert_encoding($value, 'UTF-8', 'UTF-8');
            }
        }
        return $row;
    }, $rows);
} catch (Exception $e) {
    json_error('Database error', 500);
}

json_ok(['total' => $total, 'rows' => $rows]);
