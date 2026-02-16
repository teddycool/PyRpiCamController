<?php
/**
 * NEW Version Management API - bypassing cache
 */

require_once '../utils/config.php';
require_once '../admin/admin_auth.php';

// SIMPLE TEST - Always respond for ANY upload action, regardless of method
if (isset($_GET['action']) && $_GET['action'] === 'upload') {
    sendJsonResponse(['message' => 'NEW FILE - UPLOAD ENDPOINT HIT', 'timestamp' => date('Y-m-d H:i:s')]);
}

// Debug endpoint
if (isset($_GET['debug']) && $_GET['debug'] === 'test') {
    sendJsonResponse(['message' => 'NEW FILE WORKING - CACHE CLEARED', 'timestamp' => date('Y-m-d H:i:s')]);
}

// Initialize admin session
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

// Handle other requests...
sendJsonResponse(['error' => 'Invalid action']);

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
        sendJsonResponse(['error' => 'Version is required', 'debug' => $debug], 400);
    }
    
    $version = $metadata['version'];
    $description = $metadata['description'] ?? "Version $version";
    $release_notes = $metadata['release_notes'] ?? '';
    
    // Create upload directory if it doesn't exist
    $uploadDir = '../storage/versions/';
    if (!file_exists($uploadDir)) {
        mkdir($uploadDir, 0755, true);
    }
    
    // Generate filename
    $originalName = $uploadedFile['name'];
    $extension = pathinfo($originalName, PATHINFO_EXTENSION);
    $fileName = "PyRpiCamController-{$version}.{$extension}";
    $filePath = $uploadDir . $fileName;
    
    // Move uploaded file
    if (!move_uploaded_file($uploadedFile['tmp_name'], $filePath)) {
        sendJsonResponse(['error' => 'Failed to move uploaded file'], 500);
    }
    
    // Store in database
    try {
        $stmt = $pdo->prepare("INSERT INTO versions (version, description, file_path, file_size, release_notes, release_date, status) VALUES (?, ?, ?, ?, ?, NOW(), 'active')");
        $stmt->execute([
            $version,
            $description,
            $fileName,
            filesize($filePath),
            $release_notes
        ]);
        
        sendJsonResponse(['status' => 'success', 'message' => 'Version uploaded successfully', 'version' => $version]);
    } catch (PDOException $e) {
        if ($e->getCode() == '23000') { // Duplicate key
            sendJsonResponse(['error' => 'Version already exists'], 409);
        } else {
            sendJsonResponse(['error' => 'Database error', 'details' => $e->getMessage()], 500);
        }
    }
}
?>