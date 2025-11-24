<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * OTA Update Check Endpoint
 * 
 * Endpoint: GET /api/ota/check
 * 
 * Parameters:
 * - cpu_id: Device CPU serial number
 * - current_version: Currently installed version
 * - api_key: Device API key for authentication
 * 
 * Returns:
 * - update_available: boolean
 * - version: string (if update available)
 * - download_url: string (if update available) 
 * - checksum: string (if update available)
 * - requires_reboot: boolean (if update available)
 * - release_notes: string (if update available)
 */

require_once 'config.php';

// Handle CORS and validate request
handleCors();
validateApiRequest();

// Only allow GET requests
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    sendJsonResponse(['error' => 'Method not allowed'], 405);
}

// Check maintenance mode
if (MAINTENANCE_MODE) {
    sendJsonResponse([
        'update_available' => false,
        'maintenance_mode' => true,
        'message' => 'System is in maintenance mode'
    ]);
}

// Get and validate input parameters
$cpuId = $_GET['cpu_id'] ?? '';
$currentVersion = $_GET['current_version'] ?? '';
$apiKey = $_GET['api_key'] ?? '';

// Validate required parameters
$validationErrors = validateInput($_GET, [
    'cpu_id' => ['required' => true, 'type' => 'cpu_id', 'length' => 32],
    'current_version' => ['required' => true, 'type' => 'version', 'length' => 20],
    'api_key' => ['required' => true, 'type' => 'string', 'length' => 64]
]);

if (!empty($validationErrors)) {
    logMessage('WARNING', 'Invalid update check request', [
        'errors' => $validationErrors,
        'ip' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'
    ]);
    sendJsonResponse(['error' => 'Invalid parameters', 'details' => $validationErrors], 400);
}

try {
    $pdo = getDbConnection();
    
    // Use stored procedure for secure device lookup and update check
    $stmt = $pdo->prepare("CALL GetDeviceUpdate(?, ?)");
    $stmt->execute([$cpuId, $apiKey]);
    $result = $stmt->fetch();
    
    if (!$result) {
        logMessage('WARNING', 'No update data returned for device', ['cpu_id' => $cpuId]);
        sendJsonResponse(['error' => 'Device not found or inactive'], 404);
    }
    
    // Check for errors returned by stored procedure
    if (isset($result['error'])) {
        $errorMessage = '';
        switch ($result['error']) {
            case 'INVALID_DEVICE':
                $errorMessage = 'Invalid device credentials';
                break;
            case 'UPDATES_DISABLED':
                $errorMessage = 'Updates disabled for this device';
                break;
            default:
                $errorMessage = 'Unknown error: ' . $result['error'];
        }
        
        logMessage('INFO', 'Update check rejected', [
            'cpu_id' => $cpuId,
            'error' => $result['error']
        ]);
        
        sendJsonResponse(['error' => $errorMessage], 403);
    }
    
    // Determine if update is available
    $updateAvailable = $result['update_available'] ?? false;
    $latestVersion = $result['version'] ?? $currentVersion;
    
    $response = [
        'update_available' => $updateAvailable,
        'current_version' => $currentVersion,
        'latest_version' => $latestVersion
    ];
    
    // Add update details if available
    if ($updateAvailable) {
        $response['version'] = $latestVersion;
        $response['download_url'] = $result['download_url'];
        $response['checksum'] = $result['checksum'];
        $response['file_size'] = (int)$result['file_size'];
        $response['requires_reboot'] = (bool)$result['requires_reboot'];
        $response['release_notes'] = $result['release_notes'] ?? '';
        
        // Validate download URL exists and is accessible
        if (!empty($result['download_url'])) {
            $downloadPath = str_replace(UPDATES_BASE_URL, UPDATES_BASE_PATH, $result['download_url']);
            if (!file_exists($downloadPath)) {
                logMessage('ERROR', 'Update file not found', [
                    'version' => $latestVersion,
                    'path' => $downloadPath,
                    'cpu_id' => $cpuId
                ]);
                sendJsonResponse(['error' => 'Update file not available'], 503);
            }
            
            // Add actual file size if not in database
            if (empty($result['file_size'])) {
                $response['file_size'] = filesize($downloadPath);
            }
        }
        
        logMessage('INFO', 'Update available', [
            'cpu_id' => $cpuId,
            'from_version' => $currentVersion,
            'to_version' => $latestVersion,
            'file_size' => $response['file_size']
        ]);
    } else {
        logMessage('DEBUG', 'No update available', [
            'cpu_id' => $cpuId,
            'current_version' => $currentVersion,
            'latest_version' => $latestVersion
        ]);
    }
    
    // Add optional fields
    $response['server_time'] = date('c');
    $response['api_version'] = API_VERSION;
    
    if (DEBUG_MODE) {
        $response['debug'] = [
            'device_authenticated' => true,
            'version_comparison' => version_compare($latestVersion, $currentVersion),
            'server_time' => time()
        ];
    }
    
    sendJsonResponse($response);
    
} catch (PDOException $e) {
    logMessage('ERROR', 'Database error in update check', [
        'error' => $e->getMessage(),
        'cpu_id' => $cpuId
    ]);
    sendJsonResponse(['error' => 'Internal server error'], 500);
    
} catch (Exception $e) {
    logMessage('ERROR', 'Unexpected error in update check', [
        'error' => $e->getMessage(),
        'cpu_id' => $cpuId,
        'trace' => $e->getTraceAsString()
    ]);
    sendJsonResponse(['error' => 'Internal server error'], 500);
}
?>