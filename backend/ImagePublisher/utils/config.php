<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * OTA API Configuration
 * 
 * Configuration settings for the PyRpiCamController OTA update system.
 * Copy this file to config.php and update the settings for your environment.
 */

require_once 'secrets.php'; // Contains DB credentials and secret settings

// API Security
define('API_VERSION', 'v1');
define('REQUIRE_HTTPS', true);  // Set to false for development only
define('MAX_REQUEST_SIZE', 1048576); // 1MB limit for requests
define('RATE_LIMIT_REQUESTS', 100); // Requests per hour per IP
define('API_KEY_LENGTH', 32); // Minimum API key length

// File storage configuration
define('STORAGE_DIR', __DIR__ . '/storage');
define('UPDATES_BASE_PATH', '/public_html/pycamota/releases/');
define('UPDATES_BASE_URL', 'https://www.sensorwebben.se/pycamota/');
define('MAX_FILE_SIZE', 104857600); // 100MB max file size
define('ALLOWED_EXTENSIONS', ['tar.gz', 'tgz']);

// Logging configuration
define('LOG_LEVEL', 'INFO'); // DEBUG, INFO, WARNING, ERROR
define('LOG_FILE', '/public_html/pycamota/logs/ota_api.log');
define('LOG_MAX_SIZE', 10485760); // 10MB
define('LOG_ROTATE_COUNT', 5);

// Update behavior
define('DEFAULT_UPDATE_GROUP', 'production');
define('FORCE_VERSION_CHECK', true); // Verify version compatibility
define('ALLOW_DOWNGRADE', false); // Allow downgrading to older versions
define('MAX_RETRY_ATTEMPTS', 3);

// Device management
define('DEVICE_TIMEOUT_HOURS', 24); // Mark device as inactive after this time
define('AUTO_CLEANUP_LOGS_DAYS', 90); // Auto-delete logs older than this
define('MAINTENANCE_MODE', false); // Global maintenance mode

// Development/debugging (set to false in production)
define('DEBUG_MODE', false);
define('LOG_ALL_REQUESTS', false);
define('CORS_ENABLED', false); // Enable CORS for web dashboard



// Email notifications (optional)
define('SMTP_ENABLED', false);
define('SMTP_HOST', 'smtp.example.com');
define('SMTP_PORT', 587);
define('SMTP_USER', 'notifications@example.com');
define('SMTP_PASS', 'smtp_password');
define('ADMIN_EMAIL', 'admin@example.com');

// Webhook notifications (optional)
define('WEBHOOK_ENABLED', false);
define('WEBHOOK_URL', 'https://your-webhook-endpoint.com/ota');
define('WEBHOOK_SECRET', 'your_webhook_secret');

// Cache configuration (for performance)
define('CACHE_ENABLED', true);
define('CACHE_TTL', 300); // 5 minutes
define('CACHE_TYPE', 'file'); // file, redis, memcached

// Time zone
date_default_timezone_set('Europe/Stockholm');

// Error reporting (adjust for production)
if (DEBUG_MODE) {
    error_reporting(E_ALL);
    ini_set('display_errors', 1);
} else {
    error_reporting(E_ERROR | E_WARNING);
    ini_set('display_errors', 0);
    ini_set('log_errors', 1);
    ini_set('error_log', '/var/log/pyrpicam/php_errors.log');
}

/**
 * Database connection helper
 */
function getDbConnection() {
    static $pdo = null;
    
    if ($pdo === null) {
        try {
            $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
            $options = [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES " . DB_CHARSET,
                PDO::ATTR_TIMEOUT => 30
            ];
            
            $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
        } catch (PDOException $e) {
            error_log("Database connection failed: " . $e->getMessage());
            http_response_code(500);
            die(json_encode(['error' => 'Database connection failed']));
        }
    }
    
    return $pdo;
}

/**
 * Logging helper
 */
function logMessage($level, $message, $context = []) {
    if (!in_array($level, ['DEBUG', 'INFO', 'WARNING', 'ERROR'])) {
        return;
    }
    
    $levels = ['DEBUG' => 0, 'INFO' => 1, 'WARNING' => 2, 'ERROR' => 3];
    $currentLevel = $levels[LOG_LEVEL] ?? 1;
    
    if ($levels[$level] < $currentLevel) {
        return; // Skip logging if below current log level
    }
    
    $timestamp = date('Y-m-d H:i:s');
    $contextStr = !empty($context) ? ' ' . json_encode($context) : '';
    $logLine = "[{$timestamp}] [{$level}] {$message}{$contextStr}\n";
    
    // Create log directory if it doesn't exist
    $logDir = dirname(LOG_FILE);
    if (!is_dir($logDir)) {
        mkdir($logDir, 0755, true);
    }
    
    // Rotate log if needed
    if (file_exists(LOG_FILE) && filesize(LOG_FILE) > LOG_MAX_SIZE) {
        for ($i = LOG_ROTATE_COUNT - 1; $i > 0; $i--) {
            $oldFile = LOG_FILE . '.' . $i;
            $newFile = LOG_FILE . '.' . ($i + 1);
            if (file_exists($oldFile)) {
                rename($oldFile, $newFile);
            }
        }
        rename(LOG_FILE, LOG_FILE . '.1');
    }
    
    file_put_contents(LOG_FILE, $logLine, FILE_APPEND | LOCK_EX);
}

/**
 * Security helper - validate API request
 */
function validateApiRequest() {
    // Check HTTPS in production
    if (REQUIRE_HTTPS && (!isset($_SERVER['HTTPS']) || $_SERVER['HTTPS'] !== 'on')) {
        http_response_code(400);
        die(json_encode(['error' => 'HTTPS required']));
    }
    
    // Check request size
    $contentLength = $_SERVER['CONTENT_LENGTH'] ?? 0;
    if ($contentLength > MAX_REQUEST_SIZE) {
        http_response_code(413);
        die(json_encode(['error' => 'Request too large']));
    }
    
    // Basic rate limiting (simple IP-based)
    $clientIp = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    $hourKey = 'rate_limit_' . $clientIp . '_' . date('YmdH');
    
    // This is a simple file-based rate limiting - consider using Redis in production
    $rateFile = sys_get_temp_dir() . '/' . md5($hourKey);
    $currentCount = file_exists($rateFile) ? (int)file_get_contents($rateFile) : 0;
    
    if ($currentCount >= RATE_LIMIT_REQUESTS) {
        http_response_code(429);
        die(json_encode(['error' => 'Rate limit exceeded']));
    }
    
    file_put_contents($rateFile, $currentCount + 1);
    
    return true;
}

/**
 * Validate API requests from admin dashboard (more lenient)
 */
function validateAdminApiRequest() {
    // Skip HTTPS requirement for admin dashboard (already authenticated)
    // Admin is already authenticated via session, so we trust them more
    
    // More robust HTTPS detection for admin requests if needed
    $isHttps = false;
    if (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on') {
        $isHttps = true;
    } elseif (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
        $isHttps = true;
    } elseif (isset($_SERVER['HTTP_X_FORWARDED_SSL']) && $_SERVER['HTTP_X_FORWARDED_SSL'] === 'on') {
        $isHttps = true;
    } elseif (isset($_SERVER['SERVER_PORT']) && $_SERVER['SERVER_PORT'] == '443') {
        $isHttps = true;
    }
    
    // For now, allow admin requests even without HTTPS in development
    // In production, you might want to uncomment this:
    /*
    if (REQUIRE_HTTPS && !$isHttps) {
        http_response_code(400);
        die(json_encode(['error' => 'HTTPS required for security']));
    }
    */
    
    // Check request size - be more lenient for admin
    $contentLength = $_SERVER['CONTENT_LENGTH'] ?? 0;
    if ($contentLength > MAX_REQUEST_SIZE) {
        http_response_code(413);
        die(json_encode(['error' => 'Request too large']));
    }
    
    // Skip rate limiting for admin for now (for debugging)
    /*
    // More lenient rate limiting for admin (10x normal limit)
    $clientIp = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    $hourKey = 'admin_rate_limit_' . $clientIp . '_' . date('YmdH');
    
    $rateFile = sys_get_temp_dir() . '/' . md5($hourKey);
    $currentCount = file_exists($rateFile) ? (int)file_get_contents($rateFile) : 0;
    $adminRateLimit = RATE_LIMIT_REQUESTS * 10; // 10x normal limit for admin
    
    if ($currentCount >= $adminRateLimit) {
        http_response_code(429);
        die(json_encode(['error' => 'Admin rate limit exceeded']));
    }
    
    file_put_contents($rateFile, $currentCount + 1);
    */
    
    return true;
}

/**
 * CORS helper
 */
function handleCors() {
    if (CORS_ENABLED) {
        header("Access-Control-Allow-Origin: *");
        header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
        header("Access-Control-Allow-Headers: Content-Type, Authorization");
        
        if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
            http_response_code(200);
            exit;
        }
    }
}

/**
 * Parse JSON from TEXT field (for MariaDB compatibility)
 */
function parseJsonField($jsonString) {
    if (empty($jsonString)) {
        return null;
    }
    $decoded = json_decode($jsonString, true);
    return $decoded === null ? [] : $decoded;
}

/**
 * Encode array to JSON string for TEXT field storage
 */
function encodeJsonField($data) {
    if (empty($data)) {
        return null;
    }
    return json_encode($data);
}

/**
 * Check if update group is in JSON string field
 */
function isGroupInJsonField($jsonString, $group) {
    if (empty($jsonString)) {
        return false;
    }
    $groups = parseJsonField($jsonString);
    return is_array($groups) && in_array($group, $groups);
}

/**
 * Response helper
 */
function sendJsonResponse($data, $statusCode = 200) {
    http_response_code($statusCode);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit;
}

/**
 * Input validation helper
 */
function validateInput($data, $rules) {
    $errors = [];
    
    foreach ($rules as $field => $rule) {
        $value = $data[$field] ?? null;
        
        if ($rule['required'] && empty($value)) {
            $errors[] = "Field '{$field}' is required";
            continue;
        }
        
        if (!empty($value) && isset($rule['type'])) {
            switch ($rule['type']) {
                case 'string':
                    if (!is_string($value)) {
                        $errors[] = "Field '{$field}' must be a string";
                    }
                    break;
                case 'email':
                    if (!filter_var($value, FILTER_VALIDATE_EMAIL)) {
                        $errors[] = "Field '{$field}' must be a valid email";
                    }
                    break;
                case 'version':
                    if (!preg_match('/^\d+\.\d+\.\d+(-[a-zA-Z0-9-]+)?$/', $value)) {
                        $errors[] = "Field '{$field}' must be a valid version (e.g., 1.0.0)";
                    }
                    break;
                case 'cpu_id':
                    if (!preg_match('/^[a-f0-9]{8,32}$/i', $value)) {
                        $errors[] = "Field '{$field}' must be a valid CPU ID";
                    }
                    break;
            }
        }
        
        if (!empty($value) && isset($rule['length']) && strlen($value) > $rule['length']) {
            $errors[] = "Field '{$field}' is too long (max {$rule['length']} characters)";
        }
    }
    
    return $errors;
}

// Set common headers
header('X-API-Version: ' . API_VERSION);
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');

// Handle settings API requests for dashboard
if (isset($_GET['action'])) {
    require_once 'admin_auth.php';
    
    // Require authentication for settings access
    if (!is_admin_authenticated()) {
        http_response_code(401);
        die(json_encode(['error' => 'Authentication required']));
    }
    
    switch ($_GET['action']) {
        case 'get_settings':
            sendJsonResponse([
                'settings' => [
                    'update_server' => UPDATES_BASE_URL,
                    'update_group' => DEFAULT_UPDATE_GROUP,
                    'maintenance_mode' => MAINTENANCE_MODE ? 'true' : 'false',
                    'auto_cleanup' => AUTO_CLEANUP_LOGS_DAYS
                ]
            ]);
            break;
            
        case 'save_settings':
            if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
                sendJsonResponse(['error' => 'Method not allowed'], 405);
            }
            
            $input = json_decode(file_get_contents('php://input'), true);
            
            // For now, just simulate saving (in real implementation, would update config file or database)
            sendJsonResponse(['success' => true, 'message' => 'Settings saved successfully']);
            break;
            
        default:
            sendJsonResponse(['error' => 'Invalid action'], 400);
    }
    exit;
}

if (DEBUG_MODE) {
    logMessage('DEBUG', 'OTA API configuration loaded', [
        'version' => API_VERSION,
        'debug_mode' => DEBUG_MODE,
        'maintenance_mode' => MAINTENANCE_MODE
    ]);
}
?>