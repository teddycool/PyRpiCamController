<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * OTA Status Report Endpoint
 * 
 * Endpoint: POST /api/ota/report
 * 
 * JSON Body:
 * - cpu_id: Device CPU serial number
 * - api_key: Device API key for authentication
 * - status: Update status (started, success, failed, rolled_back)
 * - version: Target version
 * - from_version: Previous version (optional)
 * - error_message: Error details (if failed)
 * - timestamp: ISO timestamp
 */

require_once 'config.php';
require_once 'admin_auth.php';

// For admin dashboard log access, require authentication
if (isset($_GET['action']) && $_GET['action'] === 'logs') {
    if (!is_admin_authenticated()) {
        http_response_code(401);
        die(json_encode(['error' => 'Authentication required']));
    }
}

// Handle CORS and validate request
handleCors();
validateApiRequest();

// Check if this is a log viewing request from dashboard
if (isset($_GET['action']) && $_GET['action'] === 'logs') {
    // Require admin auth for log viewing
    require_once 'admin_auth.php';
    require_admin_auth();
    
    // Use admin validation
    handleCors();
    validateAdminApiRequest();
    
    $logType = $_GET['type'] ?? 'ota';
    
    try {
        $logs = getLogContent($logType);
        sendJsonResponse(['logs' => $logs]);
    } catch (Exception $e) {
        error_log("Log retrieval error: " . $e->getMessage());
        sendJsonResponse(['error' => 'Failed to retrieve logs'], 500);
    }
    exit;
}

// Handle CORS and validate request for device reporting
handleCors();
validateApiRequest();

// Only allow POST requests for OTA reporting
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    sendJsonResponse(['error' => 'Method not allowed'], 405);
}

// Get JSON input
$input = json_decode(file_get_contents('php://input'), true);

if (json_last_error() !== JSON_ERROR_NONE) {
    sendJsonResponse(['error' => 'Invalid JSON'], 400);
}

// Validate required fields
$validationErrors = validateInput($input, [
    'cpu_id' => ['required' => true, 'type' => 'cpu_id', 'length' => 32],
    'api_key' => ['required' => true, 'type' => 'string', 'length' => 64],
    'status' => ['required' => true, 'type' => 'string', 'length' => 20],
    'version' => ['required' => true, 'type' => 'version', 'length' => 20],
    'timestamp' => ['required' => true, 'type' => 'string', 'length' => 30]
]);

if (!empty($validationErrors)) {
    logMessage('WARNING', 'Invalid status report request', [
        'errors' => $validationErrors,
        'ip' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'
    ]);
    sendJsonResponse(['error' => 'Invalid parameters', 'details' => $validationErrors], 400);
}

// Validate status value
$validStatuses = ['started', 'downloading', 'installing', 'success', 'failed', 'rolled_back'];
if (!in_array($input['status'], $validStatuses)) {
    sendJsonResponse([
        'error' => 'Invalid status',
        'valid_statuses' => $validStatuses
    ], 400);
}

// Extract parameters
$cpuId = $input['cpu_id'];
$apiKey = $input['api_key'];
$status = $input['status'];
$toVersion = $input['version'];
$fromVersion = $input['from_version'] ?? null;
$errorMessage = $input['error_message'] ?? null;
$timestamp = $input['timestamp'];
$clientIp = $_SERVER['REMOTE_ADDR'] ?? 'unknown';

// Validate timestamp
try {
    $reportTime = new DateTime($timestamp);
} catch (Exception $e) {
    sendJsonResponse(['error' => 'Invalid timestamp format'], 400);
}

try {
    $pdo = getDbConnection();
    
    // Use stored procedure to log the status securely
    $stmt = $pdo->prepare("CALL LogOTAStatus(?, ?, ?, ?, ?, ?, ?)");
    $stmt->execute([
        $cpuId,
        $apiKey,
        $fromVersion,
        $toVersion,
        $status,
        $errorMessage,
        $clientIp
    ]);
    
    // Get the result to check if device was valid
    $result = $stmt->fetch();
    
    if ($stmt->rowCount() === 0) {
        // Device validation failed in stored procedure
        logMessage('WARNING', 'Status report from invalid device', [
            'cpu_id' => $cpuId,
            'status' => $status,
            'ip' => $clientIp
        ]);
        sendJsonResponse(['error' => 'Invalid device credentials'], 403);
    }
    
    // Log the status report
    $logContext = [
        'cpu_id' => $cpuId,
        'status' => $status,
        'version' => $toVersion,
        'ip' => $clientIp
    ];
    
    if ($fromVersion) {
        $logContext['from_version'] = $fromVersion;
    }
    
    if ($errorMessage) {
        $logContext['error'] = $errorMessage;
    }
    
    $logLevel = ($status === 'failed') ? 'WARNING' : 'INFO';
    logMessage($logLevel, "OTA status report: {$status}", $logContext);
    
    // Send notifications for important events
    if (in_array($status, ['success', 'failed', 'rolled_back'])) {
        sendNotification($cpuId, $status, $fromVersion, $toVersion, $errorMessage);
    }
    
    // Prepare response
    $response = [
        'status' => 'success',
        'message' => 'Status report received',
        'timestamp' => date('c'),
        'api_version' => API_VERSION
    ];
    
    // Add debug info if enabled
    if (DEBUG_MODE) {
        $response['debug'] = [
            'received_at' => date('c'),
            'processed_status' => $status,
            'client_ip' => $clientIp
        ];
    }
    
    sendJsonResponse($response);
    
} catch (PDOException $e) {
    logMessage('ERROR', 'Database error in status report', [
        'error' => $e->getMessage(),
        'cpu_id' => $cpuId,
        'status' => $status
    ]);
    sendJsonResponse(['error' => 'Internal server error'], 500);
    
} catch (Exception $e) {
    logMessage('ERROR', 'Unexpected error in status report', [
        'error' => $e->getMessage(),
        'cpu_id' => $cpuId,
        'status' => $status,
        'trace' => $e->getTraceAsString()
    ]);
    sendJsonResponse(['error' => 'Internal server error'], 500);
}

/**
 * Send notification for important OTA events
 */
function sendNotification($cpuId, $status, $fromVersion, $toVersion, $errorMessage = null) {
    if (!SMTP_ENABLED && !WEBHOOK_ENABLED) {
        return; // No notifications configured
    }
    
    $subject = "OTA Update {$status}: {$cpuId}";
    $message = "Device {$cpuId} update {$status}\n";
    $message .= "From version: " . ($fromVersion ?: 'unknown') . "\n";
    $message .= "To version: {$toVersion}\n";
    $message .= "Time: " . date('Y-m-d H:i:s') . "\n";
    
    if ($errorMessage) {
        $message .= "Error: {$errorMessage}\n";
    }
    
    // Email notification
    if (SMTP_ENABLED && defined('ADMIN_EMAIL')) {
        try {
            // Simple mail sending - in production, use PHPMailer or similar
            $headers = "From: " . SMTP_USER . "\r\n";
            $headers .= "Content-Type: text/plain; charset=utf-8\r\n";
            
            mail(ADMIN_EMAIL, $subject, $message, $headers);
        } catch (Exception $e) {
            logMessage('WARNING', 'Failed to send email notification', [
                'error' => $e->getMessage()
            ]);
        }
    }
    
    // Webhook notification
    if (WEBHOOK_ENABLED && defined('WEBHOOK_URL')) {
        try {
            $payload = [
                'cpu_id' => $cpuId,
                'status' => $status,
                'from_version' => $fromVersion,
                'to_version' => $toVersion,
                'error_message' => $errorMessage,
                'timestamp' => date('c')
            ];
            
            $options = [
                'http' => [
                    'method' => 'POST',
                    'header' => "Content-Type: application/json\r\n" .
                               "X-Webhook-Secret: " . WEBHOOK_SECRET . "\r\n",
                    'content' => json_encode($payload),
                    'timeout' => 10
                ]
            ];
            
            $context = stream_context_create($options);
            $result = file_get_contents(WEBHOOK_URL, false, $context);
            
            logMessage('DEBUG', 'Webhook notification sent', [
                'cpu_id' => $cpuId,
                'status' => $status
            ]);
            
        } catch (Exception $e) {
            logMessage('WARNING', 'Failed to send webhook notification', [
                'error' => $e->getMessage(),
                'cpu_id' => $cpuId
            ]);
        }
    }
}

/**
 * Get log content for dashboard display
 */
function getLogContent($logType) {
    $logFile = '';
    
    switch ($logType) {
        case 'ota':
            $logFile = LOG_FILE;
            break;
        case 'system':
            $logFile = '/var/log/syslog';
            break;
        case 'errors':
            $logFile = '/var/log/php_errors.log';
            break;
        default:
            $logFile = LOG_FILE;
    }
    
    // Check if log file exists
    if (!file_exists($logFile)) {
        return "Loggfil hittades inte: {$logFile}\n\nDetta är normalt om systemet nyligen installerats.\nLoggar skapas automatiskt när aktivitet uppstår.";
    }
    
    if (!is_readable($logFile)) {
        return "Kan inte läsa loggfil: {$logFile}\n\nKontrollera filbehörigheter.";
    }
    
    // Get file size to avoid reading huge files
    $fileSize = filesize($logFile);
    if ($fileSize === false || $fileSize === 0) {
        return "Loggfilen är tom eller kan inte läsas.\n\nDetta är normalt för en nyinstallation.";
    }
    
    if ($fileSize > 1048576) { // 1MB
        return "Loggfilen är för stor att visa (> 1MB).\n\nAnvänd terminal för att visa: tail -f {$logFile}";
    }
    
    try {
        // Read last 100 lines
        $lines = [];
        $file = new SplFileObject($logFile);
        $file->seek(PHP_INT_MAX);
        $totalLines = $file->key();
        
        if ($totalLines === 0) {
            return "Loggfilen är tom.\n\nDetta är normalt för en nyinstallation.";
        }
        
        $startLine = max(0, $totalLines - 100);
        $file->seek($startLine);
        
        for ($i = $startLine; $i <= $totalLines; $i++) {
            $file->seek($i);
            $line = $file->current();
            if (!empty(trim($line))) {
                $lines[] = $line;
            }
        }
        
        if (empty($lines)) {
            return "Inga loggposter hittades.\n\nDetta är normalt för en nyinstallation.";
        }
        
        return implode('', $lines);
        
    } catch (Exception $e) {
        return "Fel vid läsning av loggfil: " . $e->getMessage() . "\n\nKontrollera att filen existerar och har rätt behörigheter.";
    }
}
?>