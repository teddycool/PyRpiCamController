<?php
/**
 * POST /api/hardware_info
 *
 * Device authenticates with device_id + api_key and reports hardware metadata.
 * Called once during enrollment.
 *
 * Request JSON:
 * {
 *   "device_id": "000000009fd85460",
 *   "api_key":   "sha256hex...",
 *   "hardware": {
 *     "platform":         "Rpi3B+",
 *     "memory_gb":        1,
 *     "camera_module":    "PiCam3",
 *     "hat_installed":    "None",
 *     "lightbox_enabled": true,
 *     "has_ds18b20":      true,
 *     "has_display":      true
 *   }
 * }
 */

// Always respond with JSON, even for fatal errors caught below.
header('Content-Type: application/json; charset=utf-8');

// Helper: send JSON and exit.
function hw_respond(int $status, array $body): void
{
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

try {
    // Only allow POST
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        hw_respond(405, ['success' => false, 'error' => 'Method not allowed']);
    }

    // Load DB connection via shared config
    require_once __DIR__ . '/../utils/helpers.php';
    $pdo = cam_db();

    // Parse JSON body
    $raw = file_get_contents('php://input');
    if ($raw === false || $raw === '') {
        hw_respond(400, ['success' => false, 'error' => 'Empty request body']);
    }
    $input = json_decode($raw, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        hw_respond(400, ['success' => false, 'error' => 'Invalid JSON: ' . json_last_error_msg()]);
    }

    // Validate required fields
    $device_id = isset($input['device_id']) ? trim((string)$input['device_id']) : '';
    $api_key   = isset($input['api_key'])   ? trim((string)$input['api_key'])   : '';
    $hardware  = isset($input['hardware'])  ? $input['hardware'] : null;

    if ($device_id === '') { hw_respond(400, ['success' => false, 'error' => 'Missing field: device_id']); }
    if ($api_key   === '') { hw_respond(400, ['success' => false, 'error' => 'Missing field: api_key']);   }
    if (!is_array($hardware)) { hw_respond(400, ['success' => false, 'error' => 'Field hardware must be a JSON object']); }

    // Authenticate device
    $auth = $pdo->prepare(
        'SELECT id FROM cam_devices WHERE device_id = ? AND api_key = ? AND is_active = 1 LIMIT 1'
    );
    $auth->execute([$device_id, $api_key]);
    $device = $auth->fetch(PDO::FETCH_ASSOC);

    if (!$device) {
        hw_respond(401, ['success' => false, 'error' => 'Invalid device_id or api_key']);
    }

    $device_internal_id = (int)$device['id'];

    // Update last_seen (best-effort)
    try {
        $pdo->prepare('UPDATE cam_devices SET last_seen = UTC_TIMESTAMP(), last_ip = ? WHERE id = ?')
            ->execute([$_SERVER['REMOTE_ADDR'] ?? null, $device_internal_id]);
    } catch (Exception $e) { /* non-fatal */ }

    // Extract hardware fields (all optional)
    $platform         = isset($hardware['platform'])         ? (string)$hardware['platform']       : null;
    $memory_gb        = isset($hardware['memory_gb'])        ? (int)$hardware['memory_gb']          : null;
    $camera_module    = isset($hardware['camera_module'])    ? (string)$hardware['camera_module']   : null;
    $hat_installed    = isset($hardware['hat_installed'])    ? (string)$hardware['hat_installed']   : null;
    $lightbox_enabled = !empty($hardware['lightbox_enabled']) ? 1 : 0;
    $has_ds18b20      = !empty($hardware['has_ds18b20'])     ? 1 : 0;
    $has_display      = !empty($hardware['has_display'])     ? 1 : 0;

    if ($memory_gb !== null && ($memory_gb < 1 || $memory_gb > 64)) {
        hw_respond(400, ['success' => false, 'error' => 'Invalid memory_gb (must be 1–64)']);
    }

    // Write hardware metadata to cam_devices
    $upd = $pdo->prepare('
        UPDATE cam_devices SET
            platform                  = ?,
            memory_gb                 = ?,
            camera_module             = ?,
            hat_installed             = ?,
            lightbox_enabled          = ?,
            has_ds18b20               = ?,
            has_display               = ?,
            hardware_info_reported_at = UTC_TIMESTAMP(),
            hardware_info_source      = ?
        WHERE id = ?
    ');
    $upd->execute([
        $platform, $memory_gb, $camera_module, $hat_installed,
        $lightbox_enabled, $has_ds18b20, $has_display,
        'enrollment', $device_internal_id,
    ]);

    hw_respond(200, [
        'success'   => true,
        'message'   => 'Hardware metadata updated',
        'device_id' => $device_id,
        'updated_at' => gmdate('Y-m-d\TH:i:s\Z'),
        'hardware_recorded' => [
            'platform'      => $platform,
            'memory_gb'     => $memory_gb,
            'camera_module' => $camera_module,
            'hat_installed' => $hat_installed,
            'lightbox'      => (bool)$lightbox_enabled,
            'ds18b20'       => (bool)$has_ds18b20,
            'display'       => (bool)$has_display,
        ],
    ]);

} catch (PDOException $e) {
    hw_respond(500, ['success' => false, 'error' => 'Database error', 'detail' => $e->getMessage()]);
} catch (Throwable $e) {
    hw_respond(500, ['success' => false, 'error' => 'Internal error', 'detail' => $e->getMessage()]);
}
