<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * Device Management API
 * 
 * Endpoints:
 * GET /api/devices - List all devices
 * POST /api/devices - Register new device
 * PUT /api/devices/{cpu_id} - Update device
 * DELETE /api/devices/{cpu_id} - Delete device
 * GET /api/devices/{cpu_id}/logs - Get device update logs
 * POST /api/devices/{cpu_id}/force-update - Force update to specific version
 */

require_once 'config.php';
require_once 'admin_auth.php';

// For admin dashboard access, require authentication
if (isset($_GET['action']) && in_array($_GET['action'], ['list', 'update', 'delete'])) {
    error_log("Device management: Admin action requested: " . $_GET['action']);
    
    if (!is_admin_authenticated()) {
        error_log("Device management: Authentication failed");
        http_response_code(401);
        die(json_encode(['error' => 'Authentication required']));
    }
    
    error_log("Device management: Authentication successful, using admin validation");
    // Skip some validation for authenticated admin requests
    handleCors();
    
    try {
        validateAdminApiRequest();
        error_log("Device management: Admin API validation successful");
    } catch (Exception $e) {
        error_log("Device management: Admin API validation failed: " . $e->getMessage());
        http_response_code(400);
        die(json_encode(['error' => 'Validation failed: ' . $e->getMessage()]));
    }
} else {
    error_log("Device management: Standard device API request");
    // Standard validation for device API requests
    handleCors();
    validateApiRequest();
}

// Check if this is a simple query parameter request from dashboard
if (isset($_GET['action'])) {
    try {
        $pdo = getDbConnection();
        if (!$pdo) {
            throw new Exception('Database connection failed');
        }
        
        switch ($_GET['action']) {
            case 'list':
                listDevices($pdo);
                break;
            case 'update':
                if (isset($_POST['device_id']) || isset($_GET['device_id'])) {
                    $deviceId = $_POST['device_id'] ?? $_GET['device_id'];
                    forceUpdate($pdo, $deviceId);
                } else {
                    sendJsonResponse(['error' => 'Device ID required'], 400);
                }
                break;
            case 'delete':
                if (isset($_POST['device_id']) || isset($_GET['device_id'])) {
                    $deviceId = $_POST['device_id'] ?? $_GET['device_id'];
                    deleteDevice($pdo, $deviceId);
                } else {
                    sendJsonResponse(['error' => 'Device ID required'], 400);
                }
                break;
            default:
                sendJsonResponse(['error' => 'Invalid action'], 400);
        }
    } catch (Exception $e) {
        error_log("Device management error: " . $e->getMessage());
        sendJsonResponse(['error' => 'Internal server error'], 500);
    }
    exit;
}

// Parse the URL to determine action
$requestUri = $_SERVER['REQUEST_URI'];
$urlPath = parse_url($requestUri, PHP_URL_PATH);
$pathParts = explode('/', trim($urlPath, '/'));

// Check if this is a RESTful API call (not a query parameter call)
$isRestfulCall = false;
if (count($pathParts) >= 2 && $pathParts[0] === 'api' && $pathParts[1] === 'devices') {
    // Only treat as RESTful if there's no query parameter action
    $isRestfulCall = !isset($_GET['action']);
}

// Only process RESTful API calls here
if ($isRestfulCall) {
    $cpuId = $pathParts[2] ?? null;
    $action = $pathParts[3] ?? null;
    $method = $_SERVER['REQUEST_METHOD'];

try {
    $pdo = getDbConnection();
    
    switch ($method) {
        case 'GET':
            if ($cpuId === null) {
                // List all devices
                listDevices($pdo);
            } elseif ($action === 'logs') {
                // Get device logs
                getDeviceLogs($pdo, $cpuId);
            } else {
                // Get specific device
                getDevice($pdo, $cpuId);
            }
            break;
            
        case 'POST':
            if ($cpuId === null) {
                // Register new device
                registerDevice($pdo);
            } elseif ($action === 'force-update') {
                // Force update
                forceUpdate($pdo, $cpuId);
            } else {
                sendJsonResponse(['error' => 'Invalid endpoint'], 404);
            }
            break;
            
        case 'PUT':
            if ($cpuId !== null) {
                // Update device
                updateDevice($pdo, $cpuId);
            } else {
                sendJsonResponse(['error' => 'CPU ID required for update'], 400);
            }
            break;
            
        case 'DELETE':
            if ($cpuId !== null) {
                // Delete device
                deleteDevice($pdo, $cpuId);
            } else {
                sendJsonResponse(['error' => 'CPU ID required for delete'], 400);
            }
            break;
            
        default:
            sendJsonResponse(['error' => 'Method not allowed'], 405);
    }
    
} catch (Exception $e) {
    logMessage('ERROR', 'Device API error', [
        'error' => $e->getMessage(),
        'method' => $method,
        'cpu_id' => $cpuId ?? 'none',
        'trace' => $e->getTraceAsString()
    ]);
    sendJsonResponse(['error' => 'Internal server error'], 500);
}

} // End of RESTful API call processing

/**
 * List all devices with overview information
 */
function listDevices($pdo) {
    $page = (int)($_GET['page'] ?? 1);
    $limit = min((int)($_GET['limit'] ?? 50), 100); // Max 100 per page
    $offset = ($page - 1) * $limit;
    
    $filter = $_GET['filter'] ?? '';
    $status = $_GET['status'] ?? '';
    $group = $_GET['group'] ?? '';
    
    // Build WHERE clause
    $whereConditions = [];
    $params = [];
    
    if (!empty($filter)) {
        $whereConditions[] = "(d.cpu_id LIKE ? OR d.device_name LIKE ? OR d.location LIKE ?)";
        $filterParam = "%{$filter}%";
        $params[] = $filterParam;
        $params[] = $filterParam;
        $params[] = $filterParam;
    }
    
    if (!empty($status)) {
        $whereConditions[] = "d.status = ?";
        $params[] = $status;
    }
    
    if (!empty($group)) {
        $whereConditions[] = "d.update_group = ?";
        $params[] = $group;
    }
    
    $whereClause = !empty($whereConditions) ? 'WHERE ' . implode(' AND ', $whereConditions) : '';
    
    // Get total count
    try {
        $countQuery = "SELECT COUNT(*) FROM devices d {$whereClause}";
        $stmt = $pdo->prepare($countQuery);
        $stmt->execute($params);
        $totalCount = $stmt->fetchColumn();
    } catch (PDOException $e) {
        // Table might not exist or be empty
        $totalCount = 0;
    }
    
    // Get devices using the view or fallback to devices table
    $devices = [];
    try {
        $query = "
            SELECT * FROM device_overview d
            {$whereClause}
            ORDER BY d.last_seen DESC
            LIMIT {$limit} OFFSET {$offset}
        ";
        
        $stmt = $pdo->prepare($query);
        $stmt->execute($params);
        $devices = $stmt->fetchAll();
    } catch (PDOException $e) {
        // View might not exist, try devices table directly
        try {
            $query = "
                SELECT cpu_id, device_name as model, current_version, last_seen as last_contact, status
                FROM devices d
                {$whereClause}
                ORDER BY d.last_seen DESC
                LIMIT {$limit} OFFSET {$offset}
            ";
            
            $stmt = $pdo->prepare($query);
            $stmt->execute($params);
            $devices = $stmt->fetchAll();
        } catch (PDOException $e) {
            // Table doesn't exist or other error
            $devices = [];
            error_log("Device query failed: " . $e->getMessage());
        }
    }
    
    // Add update availability for each device
    foreach ($devices as &$device) {
        $device['update_available'] = checkUpdateAvailable($pdo, $device['cpu_id'], $device['current_version'], $device['update_group']);
    }
    
    // Calculate statistics for dashboard
    $stats = calculateDeviceStats($pdo);
    
    sendJsonResponse([
        'devices' => $devices,
        'pagination' => [
            'page' => $page,
            'limit' => $limit,
            'total' => $totalCount,
            'pages' => ceil($totalCount / $limit)
        ],
        'total' => $stats['total'],
        'online' => $stats['online'],
        'pending' => $stats['pending'],
        'last_activity' => $stats['last_activity']
    ]);
}

/**
 * Calculate device statistics for dashboard
 */
function calculateDeviceStats($pdo) {
    $stats = ['total' => 0, 'online' => 0, 'pending' => 0, 'last_activity' => 'Aldrig'];
    
    try {
        // Get total devices
        $stmt = $pdo->prepare("SELECT COUNT(*) as total FROM devices");
        $stmt->execute();
        $total = $stmt->fetchColumn();
        $stats['total'] = $total;
    
        // Get online devices (seen in last 24 hours)
        $stmt = $pdo->prepare("SELECT COUNT(*) as online FROM devices WHERE last_seen >= DATE_SUB(NOW(), INTERVAL 24 HOUR)");
        $stmt->execute();
        $stats['online'] = $stmt->fetchColumn();
        
        // Get pending updates
        $stmt = $pdo->prepare("SELECT COUNT(*) as pending FROM devices WHERE status = 'pending_update'");
        $stmt->execute();
        $stats['pending'] = $stmt->fetchColumn();
        
        // Get last activity
        $stmt = $pdo->prepare("SELECT MAX(last_seen) as last_activity FROM devices");
        $stmt->execute();
        $lastActivity = $stmt->fetchColumn();
        $stats['last_activity'] = $lastActivity ? date('Y-m-d H:i:s', strtotime($lastActivity)) : 'Aldrig';
        
    } catch (PDOException $e) {
        // Database tables don't exist or other error
        error_log("Stats calculation failed: " . $e->getMessage());
    }
    
    return $stats;
}

/**
 * Get specific device details
 */
function getDevice($pdo, $cpuId) {
    $stmt = $pdo->prepare("SELECT * FROM device_overview WHERE cpu_id = ?");
    $stmt->execute([$cpuId]);
    $device = $stmt->fetch();
    
    if (!$device) {
        sendJsonResponse(['error' => 'Device not found'], 404);
    }
    
    // Add latest stats
    $stmt = $pdo->prepare("
        SELECT * FROM device_stats 
        WHERE cpu_id = ? 
        ORDER BY recorded_at DESC 
        LIMIT 1
    ");
    $stmt->execute([$cpuId]);
    $device['latest_stats'] = $stmt->fetch();
    
    // Check for available updates
    $device['update_available'] = checkUpdateAvailable($pdo, $cpuId, $device['current_version'], $device['update_group']);
    
    sendJsonResponse(['device' => $device]);
}

/**
 * Register new device
 */
function registerDevice($pdo) {
    $input = json_decode(file_get_contents('php://input'), true);
    
    $validationErrors = validateInput($input, [
        'cpu_id' => ['required' => true, 'type' => 'cpu_id', 'length' => 32],
        'device_name' => ['required' => false, 'type' => 'string', 'length' => 100],
        'location' => ['required' => false, 'type' => 'string', 'length' => 200],
        'update_group' => ['required' => false, 'type' => 'string', 'length' => 50]
    ]);
    
    if (!empty($validationErrors)) {
        sendJsonResponse(['error' => 'Invalid parameters', 'details' => $validationErrors], 400);
    }
    
    // Generate unique API key
    $apiKey = generateApiKey();
    
    try {
        $stmt = $pdo->prepare("
            INSERT INTO devices (cpu_id, api_key, device_name, location, update_group, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ");
        
        $stmt->execute([
            $input['cpu_id'],
            $apiKey,
            $input['device_name'] ?? null,
            $input['location'] ?? null,
            $input['update_group'] ?? DEFAULT_UPDATE_GROUP,
            $input['notes'] ?? 'Automatically registered'
        ]);
        
        logMessage('INFO', 'Device registered', [
            'cpu_id' => $input['cpu_id'],
            'device_name' => $input['device_name'] ?? 'unnamed',
            'update_group' => $input['update_group'] ?? DEFAULT_UPDATE_GROUP
        ]);
        
        sendJsonResponse([
            'status' => 'success',
            'message' => 'Device registered successfully',
            'cpu_id' => $input['cpu_id'],
            'api_key' => $apiKey,
            'update_group' => $input['update_group'] ?? DEFAULT_UPDATE_GROUP
        ], 201);
        
    } catch (PDOException $e) {
        if ($e->getCode() == 23000) { // Duplicate key
            sendJsonResponse(['error' => 'Device already registered'], 409);
        }
        throw $e;
    }
}

/**
 * Update device information
 */
function updateDevice($pdo, $cpuId) {
    $input = json_decode(file_get_contents('php://input'), true);
    
    $allowedFields = ['device_name', 'location', 'status', 'update_enabled', 'update_group', 'target_version', 'notes'];
    $updates = [];
    $params = [];
    
    foreach ($allowedFields as $field) {
        if (isset($input[$field])) {
            $updates[] = "{$field} = ?";
            $params[] = $input[$field];
        }
    }
    
    if (empty($updates)) {
        sendJsonResponse(['error' => 'No valid fields to update'], 400);
    }
    
    $params[] = $cpuId;
    
    $stmt = $pdo->prepare("
        UPDATE devices 
        SET " . implode(', ', $updates) . "
        WHERE cpu_id = ?
    ");
    
    $result = $stmt->execute($params);
    
    if ($stmt->rowCount() === 0) {
        sendJsonResponse(['error' => 'Device not found'], 404);
    }
    
    logMessage('INFO', 'Device updated', [
        'cpu_id' => $cpuId,
        'updated_fields' => array_keys($input)
    ]);
    
    sendJsonResponse(['status' => 'success', 'message' => 'Device updated successfully']);
}

/**
 * Delete device
 */
function deleteDevice($pdo, $cpuId) {
    $stmt = $pdo->prepare("DELETE FROM devices WHERE cpu_id = ?");
    $result = $stmt->execute([$cpuId]);
    
    if ($stmt->rowCount() === 0) {
        sendJsonResponse(['error' => 'Device not found'], 404);
    }
    
    logMessage('INFO', 'Device deleted', ['cpu_id' => $cpuId]);
    sendJsonResponse(['status' => 'success', 'message' => 'Device deleted successfully']);
}

/**
 * Get device update logs
 */
function getDeviceLogs($pdo, $cpuId) {
    $page = (int)($_GET['page'] ?? 1);
    $limit = min((int)($_GET['limit'] ?? 20), 100);
    $offset = ($page - 1) * $limit;
    
    $stmt = $pdo->prepare("
        SELECT ol.*, v.release_notes, v.file_size
        FROM ota_logs ol
        LEFT JOIN versions v ON ol.to_version = v.version
        WHERE ol.cpu_id = ?
        ORDER BY ol.started_at DESC
        LIMIT {$limit} OFFSET {$offset}
    ");
    
    $stmt->execute([$cpuId]);
    $logs = $stmt->fetchAll();
    
    // Get total count
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM ota_logs WHERE cpu_id = ?");
    $stmt->execute([$cpuId]);
    $totalCount = $stmt->fetchColumn();
    
    sendJsonResponse([
        'logs' => $logs,
        'pagination' => [
            'page' => $page,
            'limit' => $limit,
            'total' => $totalCount,
            'pages' => ceil($totalCount / $limit)
        ]
    ]);
}

/**
 * Force update device to specific version
 */
function forceUpdate($pdo, $cpuId) {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (empty($input['version'])) {
        sendJsonResponse(['error' => 'Version required'], 400);
    }
    
    $targetVersion = $input['version'];
    
    // Verify version exists
    $stmt = $pdo->prepare("SELECT id FROM versions WHERE version = ? AND status IN ('stable', 'testing')");
    $stmt->execute([$targetVersion]);
    
    if (!$stmt->fetch()) {
        sendJsonResponse(['error' => 'Version not found or not available'], 404);
    }
    
    // Update device target version
    $stmt = $pdo->prepare("UPDATE devices SET target_version = ? WHERE cpu_id = ?");
    $result = $stmt->execute([$targetVersion, $cpuId]);
    
    if ($stmt->rowCount() === 0) {
        sendJsonResponse(['error' => 'Device not found'], 404);
    }
    
    logMessage('INFO', 'Force update scheduled', [
        'cpu_id' => $cpuId,
        'target_version' => $targetVersion
    ]);
    
    sendJsonResponse([
        'status' => 'success',
        'message' => 'Force update scheduled',
        'target_version' => $targetVersion
    ]);
}

/**
 * Check if update is available for device
 */
function checkUpdateAvailable($pdo, $cpuId, $currentVersion, $updateGroup) {
    $stmt = $pdo->prepare("
        SELECT v.version, v.release_date, v.update_groups
        FROM versions v
        WHERE v.status = 'stable'
        AND v.version != ?
        ORDER BY v.release_date DESC
    ");
    
    $stmt->execute([$currentVersion]);
    $versions = $stmt->fetchAll();
    
    // Check each version to see if it supports the update group
    foreach ($versions as $version) {
        $groups = parseJsonField($version['update_groups']);
        if (is_array($groups) && in_array($updateGroup, $groups)) {
            if (version_compare($version['version'], $currentVersion, '>')) {
                return [
                    'available' => true,
                    'version' => $version['version'],
                    'release_date' => $version['release_date']
                ];
            }
        }
    }
    
    return ['available' => false];
}

/**
 * Generate secure API key
 */
function generateApiKey() {
    return bin2hex(random_bytes(32));
}
?>