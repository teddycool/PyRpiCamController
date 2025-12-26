<?php
// Simple device list endpoint - bypassing all the complex routing
header('Content-Type: application/json');
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once 'config.php';
require_once '../admin/admin_auth.php';

// Check authentication
if (!is_admin_authenticated()) {
    http_response_code(401);
    die(json_encode(['error' => 'Authentication required']));
}

try {
    // Simple device listing
    $pdo = getDbConnection();
    if (!$pdo) {
        throw new Exception('Database connection failed');
    }
    
    // Get devices with correct column names from our earlier investigation
    $stmt = $pdo->query("
        SELECT 
            cpu_id,
            device_name,
            location,
            current_version,
            target_version,
            last_seen,
            status,
            update_enabled,
            update_group,
            notes
        FROM devices 
        ORDER BY last_seen DESC
    ");
    
    $devices = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    // Get device count
    $countStmt = $pdo->query("SELECT COUNT(*) as total FROM devices");
    $countResult = $countStmt->fetch(PDO::FETCH_ASSOC);
    
    // Get version info  
    $versionStmt = $pdo->query("SELECT COUNT(*) as total FROM versions");
    $versionResult = $versionStmt->fetch(PDO::FETCH_ASSOC);
    
    // Success response
    echo json_encode([
        'success' => true,
        'devices' => $devices,
        'statistics' => [
            'total_devices' => (int)$countResult['total'],
            'total_versions' => (int)$versionResult['total'],
            'active_devices' => count(array_filter($devices, function($d) { 
                return $d['status'] === 'active'; 
            }))
        ],
        'message' => 'Device list retrieved successfully'
    ], JSON_PRETTY_PRINT);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Internal server error',
        'message' => $e->getMessage()
    ], JSON_PRETTY_PRINT);
}
?>