<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * Version Management API
 * 
 * Endpoints:
 * GET /api/versions - List all versions
 * POST /api/versions - Upload new version
 * PUT /api/versions/{id} - Update version metadata
 * DELETE /api/versions/{id} - Delete version
 * POST /api/versions/{id}/promote - Promote version to stable
 * POST /api/versions/{id}/rollback - Rollback version to testing
 */

require_once '../utils/config.php';
require_once 'admin_auth.php';

// Require authentication for all admin operations
require_admin_auth();

// Handle CORS and validate request for admin
handleCors();
validateAdminApiRequest();

// Check if this is a simple query parameter request from dashboard
if (isset($_GET['action'])) {
    try {
        $pdo = getDbConnection();
        switch ($_GET['action']) {
            case 'list':
                listVersions($pdo);
                break;
            case 'upload':
                uploadVersion($pdo);
                break;
            case 'delete':
                if (isset($_POST['version']) || isset($_GET['version'])) {
                    $version = $_POST['version'] ?? $_GET['version'];
                    deleteVersion($pdo, $version);
                } else {
                    sendJsonResponse(['error' => 'Version required'], 400);
                }
                break;
            default:
                sendJsonResponse(['error' => 'Invalid action'], 400);
        }
    } catch (Exception $e) {
        error_log("Version management error: " . $e->getMessage());
        sendJsonResponse(['error' => 'Internal server error'], 500);
    }
    exit;
}

// Parse the URL to determine action
$requestUri = $_SERVER['REQUEST_URI'];
$urlPath = parse_url($requestUri, PHP_URL_PATH);
$pathParts = explode('/', trim($urlPath, '/'));

// Expected format: api/versions[/{id}[/{action}]]
if (count($pathParts) < 2 || $pathParts[0] !== 'api' || $pathParts[1] !== 'versions') {
    sendJsonResponse(['error' => 'Invalid endpoint'], 404);
}

$versionId = $pathParts[2] ?? null;
$action = $pathParts[3] ?? null;
$method = $_SERVER['REQUEST_METHOD'];

try {
    $pdo = getDbConnection();
    
    switch ($method) {
        case 'GET':
            if ($versionId === null) {
                // List all versions
                listVersions($pdo);
            } else {
                // Get specific version
                getVersion($pdo, $versionId);
            }
            break;
            
        case 'POST':
            if ($versionId === null) {
                // Upload new version
                uploadVersion($pdo);
            } elseif ($action === 'promote') {
                // Promote to stable
                promoteVersion($pdo, $versionId);
            } elseif ($action === 'rollback') {
                // Rollback to testing
                rollbackVersion($pdo, $versionId);
            } else {
                sendJsonResponse(['error' => 'Invalid endpoint'], 404);
            }
            break;
            
        case 'PUT':
            if ($versionId !== null) {
                // Update version metadata
                updateVersion($pdo, $versionId);
            } else {
                sendJsonResponse(['error' => 'Version ID required for update'], 400);
            }
            break;
            
        case 'DELETE':
            if ($versionId !== null) {
                // Delete version
                deleteVersion($pdo, $versionId);
            } else {
                sendJsonResponse(['error' => 'Version ID required for delete'], 400);
            }
            break;
            
        default:
            sendJsonResponse(['error' => 'Method not allowed'], 405);
    }
    
} catch (Exception $e) {
    logMessage('ERROR', 'Version API error', [
        'error' => $e->getMessage(),
        'method' => $method,
        'version_id' => $versionId ?? 'none',
        'trace' => $e->getTraceAsString()
    ]);
    sendJsonResponse(['error' => 'Internal server error'], 500);
}

/**
 * List all versions with filtering and pagination
 */
function listVersions($pdo) {
    $page = (int)($_GET['page'] ?? 1);
    $limit = min((int)($_GET['limit'] ?? 20), 100);
    $offset = ($page - 1) * $limit;
    
    $status = $_GET['status'] ?? '';
    $updateGroup = $_GET['update_group'] ?? '';
    $minVersion = $_GET['min_version'] ?? '';
    
    // Build WHERE clause
    $whereConditions = [];
    $params = [];
    
    if (!empty($status)) {
        $whereConditions[] = "status = ?";
        $params[] = $status;
    }
    
    if (!empty($minVersion)) {
        $whereConditions[] = "version >= ?";
        $params[] = $minVersion;
    }
    
    $whereClause = !empty($whereConditions) ? 'WHERE ' . implode(' AND ', $whereConditions) : '';
    
    $totalCount = 0;
    $versions = [];
    
    try {
        // Get total count
        $countQuery = "SELECT COUNT(*) FROM versions {$whereClause}";
        $stmt = $pdo->prepare($countQuery);
        $stmt->execute($params);
        $totalCount = $stmt->fetchColumn();
        
        // Get versions with usage statistics
        $query = "
            SELECT 
                v.*,
                COUNT(d.cpu_id) as device_count,
                GROUP_CONCAT(DISTINCT d.update_group) as used_by_groups
            FROM versions v
            LEFT JOIN devices d ON v.version = d.current_version
            {$whereClause}
            GROUP BY v.id
            ORDER BY v.release_date DESC
            LIMIT {$limit} OFFSET {$offset}
        ";
        
        $stmt = $pdo->prepare($query);
        $stmt->execute($params);
        $versions = $stmt->fetchAll();
        
    } catch (PDOException $e) {
        // Table might not exist or other error
        error_log("Version query failed: " . $e->getMessage());
        $versions = [];
        $totalCount = 0;
    }
    
    $filterByGroup = !empty($updateGroup);
    
    // Add download statistics
    foreach ($versions as $key => &$version) {
        $version['update_groups'] = parseJsonField($version['update_groups']);
        $version['used_by_groups'] = $version['used_by_groups'] ? explode(',', $version['used_by_groups']) : [];
        
        // Filter by update group if specified
        if ($filterByGroup && !empty($updateGroup)) {
            if (!is_array($version['update_groups']) || !in_array($updateGroup, $version['update_groups'])) {
                unset($versions[$key]);
                continue;
            }
        }
        
        // Get download count
        $stmt = $pdo->prepare("
            SELECT COUNT(*) as downloads,
                   COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_updates
            FROM ota_logs 
            WHERE to_version = ?
        ");
        $stmt->execute([$version['version']]);
        $stats = $stmt->fetch();
        $version['downloads'] = (int)$stats['downloads'];
        $version['successful_updates'] = (int)$stats['successful_updates'];
    }
    
    sendJsonResponse([
        'versions' => array_values($versions), // Re-index array after filtering
        'pagination' => [
            'page' => $page,
            'limit' => $limit,
            'total' => count($versions), // Update total after filtering
            'pages' => ceil(count($versions) / $limit)
        ]
    ]);
}

/**
 * Get specific version details
 */
function getVersion($pdo, $versionId) {
    $stmt = $pdo->prepare("SELECT * FROM versions WHERE id = ?");
    $stmt->execute([$versionId]);
    $version = $stmt->fetch();
    
    if (!$version) {
        sendJsonResponse(['error' => 'Version not found'], 404);
    }
    
    $version['update_groups'] = parseJsonField($version['update_groups']);
    
    // Get device usage
    $stmt = $pdo->prepare("
        SELECT cpu_id, device_name, location, last_seen
        FROM devices 
        WHERE current_version = ?
        ORDER BY last_seen DESC
    ");
    $stmt->execute([$version['version']]);
    $version['devices'] = $stmt->fetchAll();
    
    // Get update statistics
    $stmt = $pdo->prepare("
        SELECT 
            status,
            COUNT(*) as count,
            AVG(CASE WHEN status = 'completed' THEN 
                TIMESTAMPDIFF(SECOND, started_at, completed_at) 
                ELSE NULL END) as avg_duration
        FROM ota_logs 
        WHERE to_version = ?
        GROUP BY status
    ");
    $stmt->execute([$version['version']]);
    $version['update_stats'] = $stmt->fetchAll();
    
    sendJsonResponse(['version' => $version]);
}

/**
 * Upload new version
 */
function uploadVersion($pdo) {
    // Check if file was uploaded
    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        sendJsonResponse(['error' => 'No file uploaded or upload error'], 400);
    }
    
    $uploadedFile = $_FILES['file'];
    $metadata = json_decode($_POST['metadata'] ?? '{}', true);
    
    // Validate metadata
    $validationErrors = validateInput($metadata, [
        'version' => ['required' => true, 'type' => 'string', 'length' => 50],
        'description' => ['required' => false, 'type' => 'string', 'length' => 1000],
        'release_notes' => ['required' => false, 'type' => 'string', 'length' => 5000],
        'update_groups' => ['required' => false, 'type' => 'array'],
        'min_version' => ['required' => false, 'type' => 'string', 'length' => 50]
    ]);
    
    if (!empty($validationErrors)) {
        sendJsonResponse(['error' => 'Invalid metadata', 'details' => $validationErrors], 400);
    }
    
    // Validate version format (semantic versioning)
    if (!preg_match('/^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$/', $metadata['version'])) {
        sendJsonResponse(['error' => 'Invalid version format. Use semantic versioning (e.g., 1.0.0)'], 400);
    }
    
    // Check if version already exists
    $stmt = $pdo->prepare("SELECT id FROM versions WHERE version = ?");
    $stmt->execute([$metadata['version']]);
    if ($stmt->fetch()) {
        sendJsonResponse(['error' => 'Version already exists'], 409);
    }
    
    // Validate file
    if (!str_ends_with($uploadedFile['name'], '.tar.gz')) {
        sendJsonResponse(['error' => 'Invalid file type. Only .tar.gz files allowed'], 400);
    }
    
    $maxFileSize = 500 * 1024 * 1024; // 500MB
    if ($uploadedFile['size'] > $maxFileSize) {
        sendJsonResponse(['error' => 'File too large. Maximum size: 500MB'], 400);
    }
    
    try {
        $pdo->beginTransaction();
        
        // Create storage directory
        $storageDir = STORAGE_DIR . "/versions/{$metadata['version']}";
        if (!mkdir($storageDir, 0755, true) && !is_dir($storageDir)) {
            throw new Exception("Failed to create storage directory");
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
                file_size, checksum, update_groups, min_version, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'testing')
        ");
        
        $stmt->execute([
            $metadata['version'],
            $metadata['description'] ?? '',
            $metadata['release_notes'] ?? '',
            $fileName,
            $filePath,
            $uploadedFile['size'],
            $checksum,
            json_encode($metadata['update_groups'] ?? ['stable']),
            $metadata['min_version'] ?? '0.0.0'
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

/**
 * Update version metadata
 */
function updateVersion($pdo, $versionId) {
    $input = json_decode(file_get_contents('php://input'), true);
    
    $allowedFields = ['description', 'release_notes', 'update_groups', 'min_version'];
    $updates = [];
    $params = [];
    
    foreach ($allowedFields as $field) {
        if (isset($input[$field])) {
            if ($field === 'update_groups') {
                $updates[] = "{$field} = ?";
                $params[] = json_encode($input[$field]);
            } else {
                $updates[] = "{$field} = ?";
                $params[] = $input[$field];
            }
        }
    }
    
    if (empty($updates)) {
        sendJsonResponse(['error' => 'No valid fields to update'], 400);
    }
    
    $params[] = $versionId;
    
    $stmt = $pdo->prepare("
        UPDATE versions 
        SET " . implode(', ', $updates) . "
        WHERE id = ?
    ");
    
    $result = $stmt->execute($params);
    
    if ($stmt->rowCount() === 0) {
        sendJsonResponse(['error' => 'Version not found'], 404);
    }
    
    logMessage('INFO', 'Version updated', [
        'version_id' => $versionId,
        'updated_fields' => array_keys($input)
    ]);
    
    sendJsonResponse(['status' => 'success', 'message' => 'Version updated successfully']);
}

/**
 * Promote version to stable
 */
function promoteVersion($pdo, $versionId) {
    $stmt = $pdo->prepare("
        UPDATE versions 
        SET status = 'stable' 
        WHERE id = ? AND status = 'testing'
    ");
    
    $result = $stmt->execute([$versionId]);
    
    if ($stmt->rowCount() === 0) {
        sendJsonResponse(['error' => 'Version not found or not in testing status'], 404);
    }
    
    // Get version info for logging
    $stmt = $pdo->prepare("SELECT version FROM versions WHERE id = ?");
    $stmt->execute([$versionId]);
    $version = $stmt->fetchColumn();
    
    logMessage('INFO', 'Version promoted to stable', [
        'version_id' => $versionId,
        'version' => $version
    ]);
    
    sendJsonResponse(['status' => 'success', 'message' => 'Version promoted to stable']);
}

/**
 * Rollback version to testing
 */
function rollbackVersion($pdo, $versionId) {
    $stmt = $pdo->prepare("
        UPDATE versions 
        SET status = 'testing' 
        WHERE id = ? AND status = 'stable'
    ");
    
    $result = $stmt->execute([$versionId]);
    
    if ($stmt->rowCount() === 0) {
        sendJsonResponse(['error' => 'Version not found or not in stable status'], 404);
    }
    
    // Get version info for logging
    $stmt = $pdo->prepare("SELECT version FROM versions WHERE id = ?");
    $stmt->execute([$versionId]);
    $version = $stmt->fetchColumn();
    
    logMessage('INFO', 'Version rolled back to testing', [
        'version_id' => $versionId,
        'version' => $version
    ]);
    
    sendJsonResponse(['status' => 'success', 'message' => 'Version rolled back to testing']);
}

/**
 * Delete version
 */
function deleteVersion($pdo, $versionId) {
    try {
        $pdo->beginTransaction();
        
        // Get version info before deletion
        $stmt = $pdo->prepare("SELECT version, file_path FROM versions WHERE id = ?");
        $stmt->execute([$versionId]);
        $versionInfo = $stmt->fetch();
        
        if (!$versionInfo) {
            sendJsonResponse(['error' => 'Version not found'], 404);
        }
        
        // Check if version is in use by any devices
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM devices WHERE current_version = ? OR target_version = ?");
        $stmt->execute([$versionInfo['version'], $versionInfo['version']]);
        $usageCount = $stmt->fetchColumn();
        
        if ($usageCount > 0) {
            sendJsonResponse(['error' => 'Cannot delete version that is in use by devices'], 409);
        }
        
        // Delete version record
        $stmt = $pdo->prepare("DELETE FROM versions WHERE id = ?");
        $stmt->execute([$versionId]);
        
        // Delete file
        if (file_exists($versionInfo['file_path'])) {
            unlink($versionInfo['file_path']);
        }
        
        // Remove directory if empty
        $dir = dirname($versionInfo['file_path']);
        if (is_dir($dir) && count(scandir($dir)) == 2) { // Only . and ..
            rmdir($dir);
        }
        
        $pdo->commit();
        
        logMessage('INFO', 'Version deleted', [
            'version_id' => $versionId,
            'version' => $versionInfo['version']
        ]);
        
        sendJsonResponse(['status' => 'success', 'message' => 'Version deleted successfully']);
        
    } catch (Exception $e) {
        $pdo->rollback();
        throw $e;
    }
}
?>