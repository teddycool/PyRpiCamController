<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

// Force clear OPcache for this file
if (function_exists('opcache_invalidate')) {
    opcache_invalidate(__FILE__, true);
}
if (function_exists('opcache_reset')) {
    opcache_reset();
}

/**
 * Version Management API
 * 
 * Simplified API - All admin operations use POST with JSON body
 */

require_once '../utils/config.php';
require_once '../admin/admin_auth.php';

// SIMPLE TEST - Always respond for ANY upload action, regardless of method
if (isset($_GET['action']) && $_GET['action'] === 'upload') {
    sendJsonResponse(['message' => 'UPLOAD ENDPOINT HIT - FILE UPDATED', 'timestamp' => date('Y-m-d H:i:s')]);
}

// CRITICAL: Initialize admin session FIRST before any authentication checks
start_admin_session();

// Check for file upload FIRST (before authentication)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_GET['action']) && $_GET['action'] === 'upload') {
    // Perform authentication check specifically for upload
    if (!is_admin_authenticated()) {
        sendJsonResponse(['error' => 'Authentication required for upload'], 401);
    }
    
    try {
        $pdo = getDbConnection();
        uploadVersion($pdo);
    } catch (Exception $e) {
        sendJsonResponse(['error' => 'Upload error', 'details' => $e->getMessage()], 500);
    }
    exit;
}

// IMMEDIATE DEBUG - This should show up if the new file is loaded
if (isset($_GET['debug']) && $_GET['debug'] === 'test') {
    sendJsonResponse(['message' => 'File updated at 2026-01-11 12:30:00 - TEST VERSION', 'timestamp' => date('Y-m-d H:i:s')]);
}

// AUTH TEST - Check if authentication is working
if (isset($_GET['debug']) && $_GET['debug'] === 'auth') {
    // Session already started at the top of the file
    $authStatus = [
        'session_name' => session_name(),
        'session_id' => session_id(),
        'session_data' => $_SESSION ?? [],
        'is_authenticated' => is_admin_authenticated(),
        'cookies' => $_COOKIE ?? [],
        'admin_session_name' => defined('ADMIN_SESSION_NAME') ? ADMIN_SESSION_NAME : 'not defined',
        'timestamp' => date('Y-m-d H:i:s')
    ];
    sendJsonResponse(['auth_debug' => $authStatus]);
}

// Enhanced debugging for upload requests
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_GET['action'])) {
    $debugInfo = [
        'method' => $_SERVER['REQUEST_METHOD'],
        'action_param' => $_GET['action'],
        'all_get' => $_GET,
        'has_files' => !empty($_FILES),
        'request_uri' => $_SERVER['REQUEST_URI'],
        'content_type' => $_SERVER['CONTENT_TYPE'] ?? 'not set',
        'session_id' => session_id(),
        'session_data' => $_SESSION ?? [],
        'cookies' => $_COOKIE ?? [],
        'session_name' => session_name(),
        'auth_check' => is_admin_authenticated() ? 'authenticated' : 'not authenticated'
    ];
    
    // Log debug info for upload requests but don't return early
    if ($_GET['action'] === 'upload') {
        error_log('Upload request debug: ' . json_encode($debugInfo));
    }
}

// Require authentication for all admin operations
require_admin_auth();

// Handle CORS and validate request for admin
handleCors();
validateAdminApiRequest();

// Create debug info to return in response
$debug = [
    'request_method' => $_SERVER['REQUEST_METHOD'],
    'get_params' => $_GET,
    'post_params' => $_POST,
    'files_keys' => array_keys($_FILES),
    'content_type' => $_SERVER['CONTENT_TYPE'] ?? 'not set'
];

// Handle other POST requests with JSON body
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $debug['path_taken'] = 'JSON';
    
    try {
        $pdo = getDbConnection();
        
        // Parse JSON body for other requests
        $rawInput = file_get_contents('php://input');
        $debug['raw_input'] = $rawInput;
        $input = json_decode($rawInput, true);
        $debug['parsed_input'] = $input;
        
        if ($input === null) {
            $debug['error_reason'] = 'JSON is null';
            sendJsonResponse(['error' => 'Invalid JSON body', 'debug' => $debug], 400);
        }
        
        $action = $input['action'] ?? null;
        $debug['action_found'] = $action;
        
        switch ($action) {
            case 'list':
                listVersions($pdo);
                break;
            case 'delete':
                $version = $input['version'] ?? null;
                if ($version) {
                    deleteVersion($pdo, $version);
                } else {
                    sendJsonResponse(['error' => 'Version required'], 400);
                }
                break;
            default:
                $debug['error_reason'] = 'Invalid action: ' . $action;
                sendJsonResponse(['error' => 'Invalid action', 'debug' => $debug], 400);
        }
    } catch (Exception $e) {
        sendJsonResponse(['error' => 'Internal server error', 'details' => $e->getMessage(), 'debug' => $debug], 500);
    }
    exit;
}

// If we get here, it's an invalid request
sendJsonResponse(['error' => 'Invalid request method or action'], 400);

/**
 * List all versions with filtering and pagination
 */
function listVersions($pdo) {
    $versions = [];
    $totalCount = 0;
    
    try {
        // Simple query to get all versions
        $query = "SELECT id, version, description, release_date, status, file_size FROM versions ORDER BY release_date DESC";
        $stmt = $pdo->prepare($query);
        $stmt->execute();
        $versions = $stmt->fetchAll();
        $totalCount = count($versions);
        
    } catch (PDOException $e) {
        // Table might not exist or other error
        error_log("Version query failed: " . $e->getMessage());
        $versions = [];
        $totalCount = 0;
    }
    
    sendJsonResponse([
        'versions' => $versions,
        'pagination' => [
            'page' => 1,
            'limit' => 50,
            'total' => $totalCount,
            'pages' => 1
        ]
    ]);
}

/**
 * Delete version
 */
function deleteVersion($pdo, $version) {
    // First check if version exists
    $stmt = $pdo->prepare("SELECT id, file_path FROM versions WHERE version = ?");
    $stmt->execute([$version]);
    $versionData = $stmt->fetch();
    
    if (!$versionData) {
        sendJsonResponse(['error' => 'Version not found'], 404);
    }
    
    try {
        $pdo->beginTransaction();
        
        // Delete from database
        $stmt = $pdo->prepare("DELETE FROM versions WHERE version = ?");
        $stmt->execute([$version]);
        
        // Delete file if it exists
        if (!empty($versionData['file_path']) && file_exists($versionData['file_path'])) {
            unlink($versionData['file_path']);
        }
        
        $pdo->commit();
        
        logMessage('INFO', 'Version deleted', ['version' => $version]);
        sendJsonResponse(['status' => 'success', 'message' => 'Version deleted successfully']);
        
    } catch (Exception $e) {
        $pdo->rollback();
        error_log("Version deletion error: " . $e->getMessage());
        sendJsonResponse(['error' => 'Failed to delete version'], 500);
    }
}

/**
 * Upload new version (simplified version)
 */
function uploadVersion($pdo) {
    $debug = [];
    $debug['step'] = 'Starting upload';
    $debug['files'] = $_FILES;
    $debug['post'] = $_POST;
    
    // Check if file was uploaded
    if (!isset($_FILES['file'])) {
        $debug['error'] = 'No file field';
        sendJsonResponse(['error' => 'No file field in upload', 'debug' => $debug], 400);
    }
    
    if ($_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        $error = $_FILES['file']['error'];
        $errorMsg = [
            UPLOAD_ERR_INI_SIZE => 'File too large (exceeds upload_max_filesize)',
            UPLOAD_ERR_FORM_SIZE => 'File too large (exceeds MAX_FILE_SIZE)',
            UPLOAD_ERR_PARTIAL => 'File only partially uploaded',
            UPLOAD_ERR_NO_FILE => 'No file was uploaded',
            UPLOAD_ERR_NO_TMP_DIR => 'Missing temporary folder',
            UPLOAD_ERR_CANT_WRITE => 'Failed to write file to disk',
            UPLOAD_ERR_EXTENSION => 'File upload stopped by extension'
        ][$error] ?? "Unknown upload error ($error)";
        
        $debug['error'] = "Upload error: $error - $errorMsg";
        sendJsonResponse(['error' => 'File upload error', 'details' => $errorMsg, 'debug' => $debug], 400);
    }
    
    $uploadedFile = $_FILES['file'];
    $debug['step'] = 'File upload OK';
    
    // Check metadata
    if (!isset($_POST['metadata'])) {
        $debug['error'] = 'No metadata in POST';
        sendJsonResponse(['error' => 'No metadata provided', 'debug' => $debug], 400);
    }
    
    $debug['step'] = 'Metadata found';
    $debug['raw_metadata'] = $_POST['metadata'];
    
    $metadata = json_decode($_POST['metadata'], true);
    
    if ($metadata === null) {
        $debug['error'] = 'Invalid JSON in metadata';
        sendJsonResponse(['error' => 'Invalid metadata JSON', 'debug' => $debug], 400);
    }
    
    $debug['step'] = 'Metadata parsed';
    $debug['metadata'] = $metadata;
    
    // Basic validation
    if (empty($metadata['version'])) {
        $debug['error'] = 'Version missing in metadata';
        sendJsonResponse(['error' => 'Version required in metadata', 'debug' => $debug], 400);
    }
    
    // Check if version already exists
    $stmt = $pdo->prepare("SELECT id FROM versions WHERE version = ?");
    $stmt->execute([$metadata['version']]);
    if ($stmt->fetch()) {
        sendJsonResponse(['error' => 'Version already exists'], 409);
    }
    
    // Validate file type
    if (!str_ends_with($uploadedFile['name'], '.tar.gz')) {
        sendJsonResponse(['error' => 'Invalid file type. Only .tar.gz files allowed'], 400);
    }
    
    try {
        $pdo->beginTransaction();
        
        // Check if STORAGE_DIR is defined
        if (!defined('STORAGE_DIR')) {
            throw new Exception("STORAGE_DIR not defined");
        }
        
        // Create storage directory
        $storageDir = STORAGE_DIR . "/versions/{$metadata['version']}";
        error_log("Attempting to create storage dir: $storageDir");
        
        if (!mkdir($storageDir, 0755, true) && !is_dir($storageDir)) {
            throw new Exception("Failed to create storage directory: $storageDir");
        }
        
        $fileName = "PyRpiCamController-{$metadata['version']}.tar.gz";
        $filePath = $storageDir . '/' . $fileName;
        
        // Move uploaded file
        if (!move_uploaded_file($uploadedFile['tmp_name'], $filePath)) {
            throw new Exception("Failed to move uploaded file");
        }
        
        // Calculate checksum
        $checksum = hash_file('sha256', $filePath);
        
        // Insert version record
        $stmt = $pdo->prepare("
            INSERT INTO versions (
                version, description, release_notes, file_name, file_path, 
                file_size, checksum, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'testing')
        ");
        
        $stmt->execute([
            $metadata['version'],
            $metadata['description'] ?? '',
            $metadata['release_notes'] ?? '',
            $fileName,
            $filePath,
            $uploadedFile['size'],
            $checksum
        ]);
        
        $versionId = $pdo->lastInsertId();
        $pdo->commit();
        
        logMessage('INFO', 'Version uploaded', [
            'version' => $metadata['version'],
            'file_size' => $uploadedFile['size'],
            'checksum' => $checksum
        ]);
        
        sendJsonResponse([
            'status' => 'success',
            'message' => 'Version uploaded successfully',
            'version_id' => $versionId,
            'version' => $metadata['version'],
            'checksum' => $checksum
        ], 201);
        
    } catch (Exception $e) {
        $pdo->rollback();
        
        // Clean up file if it was moved
        if (isset($filePath) && file_exists($filePath)) {
            unlink($filePath);
        }
        
        throw $e;
    }
}
?>