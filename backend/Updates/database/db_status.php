<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * Database Status Check
 * 
 * Simple diagnostic script to check database connectivity and table status
 */

require_once '../admin/admin_auth.php';

// Require authentication
require_admin_auth();

header('Content-Type: application/json');

try {
    $pdo = getDbConnection();
    
    $status = [
        'database_connection' => false,
        'database_info' => [],
        'tables' => [],
        'views' => [],
        'errors' => []
    ];
    
    if ($pdo) {
        $status['database_connection'] = true;
        
        // Get database information
        try {
            $stmt = $pdo->query("SELECT DATABASE() as current_db");
            $currentDb = $stmt->fetchColumn();
            $status['database_info']['current_database'] = $currentDb;
            
            $stmt = $pdo->query("SELECT VERSION() as version");
            $version = $stmt->fetchColumn();
            $status['database_info']['server_version'] = $version;
        } catch (PDOException $e) {
            $status['database_info']['error'] = $e->getMessage();
        }
        
        // Check if required tables exist
        $tables_to_check = ['devices', 'versions', 'ota_logs'];
        
        foreach ($tables_to_check as $table) {
            try {
                // Use direct query instead of prepared statement for SHOW TABLES
                $stmt = $pdo->query("SHOW TABLES LIKE '{$table}'");
                $exists = $stmt->fetch() !== false;
                
                if ($exists) {
                    // Get row count using prepared statement (safe for table name we control)
                    $countStmt = $pdo->query("SELECT COUNT(*) FROM `{$table}`");
                    $count = $countStmt->fetchColumn();
                    
                    $status['tables'][$table] = [
                        'exists' => true,
                        'count' => $count
                    ];
                } else {
                    $status['tables'][$table] = [
                        'exists' => false,
                        'count' => 0
                    ];
                }
            } catch (PDOException $e) {
                $status['tables'][$table] = [
                    'exists' => false,
                    'count' => 0,
                    'error' => $e->getMessage()
                ];
            }
        }
        
        // Check if device_overview view exists
        try {
            // First check if the view exists in the information schema
            $stmt = $pdo->query("SELECT COUNT(*) FROM information_schema.views WHERE table_name = 'device_overview' AND table_schema = DATABASE()");
            $viewExists = $stmt->fetchColumn() > 0;
            
            if ($viewExists) {
                // Try to query the view
                $stmt = $pdo->query("SELECT 1 FROM device_overview LIMIT 1");
                $status['views']['device_overview'] = ['exists' => true];
            } else {
                $status['views']['device_overview'] = ['exists' => false];
            }
        } catch (PDOException $e) {
            $status['views']['device_overview'] = [
                'exists' => false,
                'error' => $e->getMessage()
            ];
        }
        
    } else {
        $status['errors'][] = 'Could not establish database connection';
    }
    
} catch (Exception $e) {
    $status = [
        'database_connection' => false,
        'tables' => [],
        'errors' => [$e->getMessage()]
    ];
}

echo json_encode($status, JSON_PRETTY_PRINT);
?>