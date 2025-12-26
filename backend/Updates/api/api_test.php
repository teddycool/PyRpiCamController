<?php
/**
 * Simple API test endpoint for debugging
 */

require_once '../utils/config.php';
require_once 'admin_auth.php';

// Set JSON header
header('Content-Type: application/json');

// Check authentication
if (!is_admin_authenticated()) {
    http_response_code(401);
    die(json_encode(['error' => 'Not authenticated']));
}

// Test basic API functionality
$result = [
    'status' => 'success',
    'message' => 'API test successful',
    'timestamp' => date('Y-m-d H:i:s'),
    'server_info' => [
        'https' => isset($_SERVER['HTTPS']) ? $_SERVER['HTTPS'] : 'not set',
        'require_https' => REQUIRE_HTTPS,
        'request_method' => $_SERVER['REQUEST_METHOD'],
        'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? 'not set',
        'remote_addr' => $_SERVER['REMOTE_ADDR'] ?? 'not set',
        'content_length' => $_SERVER['CONTENT_LENGTH'] ?? '0'
    ],
    'api_settings' => [
        'api_version' => API_VERSION,
        'max_request_size' => MAX_REQUEST_SIZE,
        'rate_limit' => RATE_LIMIT_REQUESTS,
        'debug_mode' => DEBUG_MODE
    ]
];

echo json_encode($result, JSON_PRETTY_PRINT);
?>