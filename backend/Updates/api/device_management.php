
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
 * Simplified API - All admin operations use POST with JSON body
 */

require_once '../utils/config.php';
require_once '../admin/admin_auth.php';

// Handle POST requests with JSON body for admin operations
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    error_log("Device management: POST request received");
    
    // Check for authentication - either session-based or HTTP Basic Auth
    $authenticated = false;
    
    // Method 1: Check session-based auth (for web dashboard)
    if (is_admin_authenticated()) {
        $authenticated = true;
        error_log("Device management: Session authentication successful");
    }
    // Method 2: Check HTTP Basic Auth (for Pi registration)
    else if (isset($_SERVER['PHP_AUTH_USER']) && isset($_SERVER['PHP_AUTH_PW'])) {
        $username = $_SERVER['PHP_AUTH_USER'];
        $password = $_SERVER['PHP_AUTH_PW'];
        
        if (authenticate_admin($username, $password)) {
            $authenticated = true;
            error_log("Device management: Basic Auth authentication successful for user: $username");
        } else {
            error_log("Device management: Basic Auth failed for user: $username");
        }
    }
    // Method 3: Check Authorization header for Basic Auth
    else if (isset($_SERVER['HTTP_AUTHORIZATION'])) {
        $auth_header = $_SERVER['HTTP_AUTHORIZATION'];
        if (preg_match('/^Basic\s+(.*)$/i', $auth_header, $matches)) {
            $credentials = base64_decode($matches[1]);
            if (strpos($credentials, ':') !== false) {
                list($username, $password) = explode(':', $credentials, 2);
                if (authenticate_admin($username, $password)) {
                    $authenticated = true;
                    error_log("Device management: Authorization header Basic Auth successful for user: $username");
                } else {
                    error_log("Device management: Authorization header Basic Auth failed for user: $username");
                }
            }
        }
    }
    
    if (!$authenticated) {
        error_log("Device management: All authentication methods failed");
        http_response_code(401);
        die(json_encode(['error' => 'Authentication required']));
    }
    handleCors();
    
    try {
        validateAdminApiRequest();
        error_log("Device management: Admin API validation successful");
    } catch (Exception $e) {
        error_log("Device management: Admin API validation failed: " . $e->getMessage());
        http_response_code(400);
        die(json_encode(['error' => 'Validation failed: ' . $e->getMessage()]));
    }
    
    // Parse JSON body for all POST requests
    $input = json_decode(file_get_contents('php://input'), true);
    if ($input === null) {
        error_log("Device management: Invalid JSON body");
        http_response_code(400);
        die(json_encode(['error' => 'Invalid JSON body']));
    }
    
    try {
        $pdo = getDbConnection();
        if (!$pdo) {
            throw new Exception('Database connection failed');
        }
        
        $action = $input['action'] ?? null;
        switch ($action) {
            case 'list':
                listDevices($pdo);
                break;
            case 'register':
                registerDevice($pdo, $input);
                break;
            case 'update':
                $deviceId = $input['device_id'] ?? null;
                if ($deviceId) {
                    forceUpdate($pdo, $deviceId);
                } else {
                    sendJsonResponse(['error' => 'Device ID required'], 400);
                }
                break;
            case 'delete':
                $deviceId = $input['device_id'] ?? null;
                if ($deviceId) {
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
} else {
    error_log("Device management: Non-POST request");
    handleCors();
    validateApiRequest();
    
    // For non-POST requests, return method not allowed
    sendJsonResponse(['error' => 'Only POST requests supported for admin operations'], 405);
}

/**
 * Register a new device
 */
function registerDevice($pdo, $input) {
    $cpuId = $input['cpu_id'] ?? null;
    $deviceName = $input['device_name'] ?? null;
    $location = $input['location'] ?? 'Unknown';
    $updateGroup = $input['update_group'] ?? 'production';
    
    if (!$cpuId) {
        sendJsonResponse(['error' => 'CPU ID required'], 400);
        return;
    }
    
    try {
        // Check if device already exists
        $stmt = $pdo->prepare("SELECT cpu_id, api_key FROM devices WHERE cpu_id = ?");
        $stmt->execute([$cpuId]);
        $existingDevice = $stmt->fetch();
        
        if ($existingDevice) {
            // Device already exists, return existing API key
            error_log("Device already registered: " . $cpuId);
            sendJsonResponse([
                'message' => 'Device already registered',
                'cpu_id' => $existingDevice['cpu_id'],
                'api_key' => $existingDevice['api_key'],
                'update_group' => $updateGroup
            ], 409);
            return;
        }
        
        // Generate new API key
        $apiKey = bin2hex(random_bytes(32));
        
        // Insert new device
        $stmt = $pdo->prepare("
            INSERT INTO devices (cpu_id, device_name, location, api_key, update_group, status, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, 'active', NOW(), NOW())
        ");
        
        $result = $stmt->execute([$cpuId, $deviceName, $location, $apiKey, $updateGroup]);
        
        if ($result) {
            error_log("Device registered successfully: " . $cpuId);
            sendJsonResponse([
                'message' => 'Device registered successfully',
                'cpu_id' => $cpuId,
                'api_key' => $apiKey,
                'update_group' => $updateGroup
            ], 201);
        } else {
            throw new Exception('Failed to insert device record');
        }
        
    } catch (PDOException $e) {
        error_log("Database error during device registration: " . $e->getMessage());
        sendJsonResponse(['error' => 'Database error during registration'], 500);
    }
}

/**
 * List all devices with overview information
 */
function listDevices($pdo) {
    $page = 1;
    $limit = 50;
    $offset = 0;
    
    // Get total count
    try {
        $countQuery = "SELECT COUNT(*) FROM devices";
        $stmt = $pdo->prepare($countQuery);
        $stmt->execute();
        $totalCount = $stmt->fetchColumn();
    } catch (PDOException $e) {
        $totalCount = 0;
    }
    
    // Get devices
    $devices = [];
    try {
        $query = "
            SELECT cpu_id, device_name, current_version, last_seen, status, update_group
            FROM devices
            ORDER BY last_seen DESC
            LIMIT {$limit} OFFSET {$offset}
        ";
        
        $stmt = $pdo->prepare($query);
        $stmt->execute();
        $devices = $stmt->fetchAll();
    } catch (PDOException $e) {
        $devices = [];
        error_log("Device query failed: " . $e->getMessage());
    }
    
    // Calculate statistics
    $stats = ['total' => $totalCount, 'online' => 0, 'pending' => 0];
    
    try {
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM devices WHERE last_seen >= DATE_SUB(NOW(), INTERVAL 24 HOUR)");
        $stmt->execute();
        $stats['online'] = $stmt->fetchColumn();
        
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM devices WHERE status = 'pending_update'");
        $stmt->execute();
        $stats['pending'] = $stmt->fetchColumn();
    } catch (PDOException $e) {
        error_log("Stats calculation failed: " . $e->getMessage());
    }
    
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
        'pending' => $stats['pending']
    ]);
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
 * Force update device to specific version
 */
function forceUpdate($pdo, $cpuId) {
    // For now, just update status
    $stmt = $pdo->prepare("UPDATE devices SET status = 'pending_update' WHERE cpu_id = ?");
    $result = $stmt->execute([$cpuId]);
    
    if ($stmt->rowCount() === 0) {
        sendJsonResponse(['error' => 'Device not found'], 404);
    }
    
    logMessage('INFO', 'Force update scheduled', ['cpu_id' => $cpuId]);
    
    sendJsonResponse([
        'status' => 'success',
        'message' => 'Force update scheduled'
    ]);
}
?>