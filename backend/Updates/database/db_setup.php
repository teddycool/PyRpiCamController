<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * Basic Database Setup for Testing
 * 
 * Creates basic tables and sample data for testing the dashboard
 */

require_once '../admin/admin_auth.php';

// Require authentication
require_admin_auth();

header('Content-Type: text/html; charset=UTF-8');
?>
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Databasinitiering - PyRpiCamController</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .code { background: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; margin: 10px 0; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 30px; }
    </style>
</head>
<body>
    <h1>🔧 Databasinitiering för PyRpiCamController</h1>
    
    <div class="warning">
        <strong>⚠️ Varning:</strong> Detta verktyg är avsett för utveckling och testning.
        Använd inte på produktionsdata utan säkerhetskopiering!
    </div>

    <?php
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
        $action = $_POST['action'];
        
        try {
            $pdo = getDbConnection();
            
            if (!$pdo) {
                throw new Exception('Could not connect to database');
            }
            
            // Show current database info
            $stmt = $pdo->query("SELECT DATABASE() as db, VERSION() as version");
            $dbInfo = $stmt->fetch();
            echo "<div class='success'>🔗 Ansluten till databas: <strong>" . htmlspecialchars($dbInfo['db']) . "</strong> (Version: " . htmlspecialchars($dbInfo['version']) . ")</div>";
            
            if ($action === 'create_tables') {
                echo "<h2>Skapar databastabeller...</h2>";
                
                // Create devices table
                $sql = "CREATE TABLE IF NOT EXISTS devices (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    cpu_id VARCHAR(32) UNIQUE NOT NULL COMMENT 'Raspberry Pi CPU serial number',
                    api_key VARCHAR(64) UNIQUE NOT NULL COMMENT 'Unique API key for this device',
                    device_name VARCHAR(100) DEFAULT NULL COMMENT 'Optional friendly name',
                    location VARCHAR(200) DEFAULT NULL COMMENT 'Device location/description',
                    current_version VARCHAR(20) DEFAULT '1.0.0' COMMENT 'Currently installed version',
                    target_version VARCHAR(20) DEFAULT NULL COMMENT 'Target version for updates',
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('active', 'inactive', 'maintenance', 'error') DEFAULT 'active',
                    update_enabled BOOLEAN DEFAULT TRUE COMMENT 'Whether OTA updates are enabled',
                    update_group VARCHAR(50) DEFAULT 'production' COMMENT 'Update group (production, beta, dev)',
                    notes TEXT DEFAULT NULL COMMENT 'Admin notes about this device',
                    INDEX idx_cpu_id (cpu_id),
                    INDEX idx_api_key (api_key),
                    INDEX idx_status (status),
                    INDEX idx_update_group (update_group)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
                
                $pdo->exec($sql);
                echo "<div class='success'>✓ Tabell 'devices' skapad</div>";
                
                // Create versions table
                $sql = "CREATE TABLE IF NOT EXISTS versions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    version VARCHAR(20) UNIQUE NOT NULL,
                    release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    download_url VARCHAR(500) NOT NULL COMMENT 'URL to download this version',
                    checksum VARCHAR(64) NOT NULL COMMENT 'SHA256 checksum of the package',
                    file_size BIGINT DEFAULT NULL COMMENT 'Package file size in bytes',
                    requires_reboot BOOLEAN DEFAULT FALSE,
                    update_groups TEXT DEFAULT NULL COMMENT 'JSON string: Which groups can receive this update',
                    min_version VARCHAR(20) DEFAULT NULL COMMENT 'Minimum version required for this update',
                    max_version VARCHAR(20) DEFAULT NULL COMMENT 'Maximum version this can update from',
                    release_notes TEXT DEFAULT NULL,
                    status ENUM('development', 'testing', 'stable', 'deprecated') DEFAULT 'development',
                    created_by VARCHAR(100) DEFAULT NULL COMMENT 'Who created this release',
                    INDEX idx_version (version),
                    INDEX idx_status (status),
                    INDEX idx_release_date (release_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
                
                $pdo->exec($sql);
                echo "<div class='success'>✓ Tabell 'versions' skapad</div>";
                
                // Create ota_logs table
                $sql = "CREATE TABLE IF NOT EXISTS ota_logs (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    cpu_id VARCHAR(32) NOT NULL,
                    update_id VARCHAR(100) UNIQUE NOT NULL COMMENT 'Unique identifier for this update attempt',
                    from_version VARCHAR(20) DEFAULT NULL,
                    to_version VARCHAR(20) NOT NULL,
                    status ENUM('started', 'downloading', 'installing', 'success', 'failed', 'rolled_back') NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL DEFAULT NULL,
                    error_message TEXT DEFAULT NULL,
                    client_ip VARCHAR(45) DEFAULT NULL,
                    user_agent TEXT DEFAULT NULL,
                    INDEX idx_cpu_id (cpu_id),
                    INDEX idx_status (status),
                    INDEX idx_update_id (update_id),
                    INDEX idx_started_at (started_at),
                    FOREIGN KEY (cpu_id) REFERENCES devices(cpu_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
                
                $pdo->exec($sql);
                echo "<div class='success'>✓ Tabell 'ota_logs' skapad</div>";
                
                // Create device_overview view
                $sql = "CREATE OR REPLACE VIEW device_overview AS
                SELECT 
                    d.*,
                    COUNT(ol.id) as total_updates,
                    MAX(ol.completed_at) as last_update_time,
                    (SELECT ol2.status FROM ota_logs ol2 WHERE ol2.cpu_id = d.cpu_id ORDER BY ol2.started_at DESC LIMIT 1) as last_update_status
                FROM devices d
                LEFT JOIN ota_logs ol ON d.cpu_id = ol.cpu_id
                GROUP BY d.id";
                
                $pdo->exec($sql);
                echo "<div class='success'>✓ Vy 'device_overview' skapad</div>";
                
                echo "<div class='success'><strong>🎉 Alla databastabeller och vyer har skapats framgångsrikt!</strong></div>";
                
            } elseif ($action === 'create_sample_data') {
                echo "<h2>Skapar exempeldata...</h2>";
                
                // Add sample devices
                $stmt = $pdo->prepare("INSERT IGNORE INTO devices (cpu_id, api_key, device_name, location, current_version, status, update_group) VALUES (?, ?, ?, ?, ?, ?, ?)");
                
                $sampleDevices = [
                    ['10000000a1b2c3d4', 'test_key_1', 'Kökskamera', 'Kök', '2.5.0', 'active', 'production'],
                    ['20000000e5f6g7h8', 'test_key_2', 'Vardagsrumskamera', 'Vardagsrum', '2.4.1', 'active', 'beta'],
                    ['30000000i9j0k1l2', 'test_key_3', 'Utekamera', 'Trädgård', '2.5.0', 'inactive', 'production'],
                ];
                
                foreach ($sampleDevices as $device) {
                    $stmt->execute($device);
                }
                echo "<div class='success'>✓ " . count($sampleDevices) . " exempelenheter tillagda</div>";
                
                // Add sample versions
                $stmt = $pdo->prepare("INSERT IGNORE INTO versions (version, download_url, checksum, file_size, status, release_notes) VALUES (?, ?, ?, ?, ?, ?)");
                
                $sampleVersions = [
                    ['3.0.0', 'https://www.sensorwebben.se/pycamota/releases/3.0.0.tar.gz', 'abc123...', 5242880, 'stable', 'Ny huvudversion med förbättrad prestanda'],
                    ['2.5.1', 'https://www.sensorwebben.se/pycamota/releases/2.5.1.tar.gz', 'def456...', 4194304, 'stable', 'Buggfixar och säkerhetsuppdateringar'],
                    ['3.1.0-beta', 'https://www.sensorwebben.se/pycamota/releases/3.1.0-beta.tar.gz', 'ghi789...', 5505024, 'testing', 'Beta-version med nya funktioner'],
                ];
                
                foreach ($sampleVersions as $version) {
                    $stmt->execute($version);
                }
                echo "<div class='success'>✓ " . count($sampleVersions) . " exempelversioner tillagda</div>";
            }
            
        } catch (PDOException $e) {
            echo "<div class='error'>❌ Databasfel: " . htmlspecialchars($e->getMessage()) . "</div>";
        } catch (Exception $e) {
            echo "<div class='error'>❌ Fel: " . htmlspecialchars($e->getMessage()) . "</div>";
        }
    }
    ?>

    <h2>Åtgärder</h2>
    
    <form method="POST" style="margin: 20px 0;">
        <input type="hidden" name="action" value="create_tables">
        <button type="submit" class="btn">📊 Skapa databastabeller</button>
        <p><small>Skapar grundtabeller för enheter, versioner och loggar</small></p>
    </form>
    
    <form method="POST" style="margin: 20px 0;">
        <input type="hidden" name="action" value="create_sample_data">
        <button type="submit" class="btn">🎭 Lägg till exempeldata</button>
        <p><small>Lägger till testenheter och versioner för att prova dashboarden</small></p>
    </form>

    <h2>Aktuell databasstatus</h2>
    
    <?php
    // Always show current status
    try {
        $pdo = getDbConnection();
        if ($pdo) {
            $stmt = $pdo->query("SELECT DATABASE() as db, VERSION() as version");
            $dbInfo = $stmt->fetch();
            echo "<div class='success'>🔗 Ansluten till databas: <strong>" . htmlspecialchars($dbInfo['db']) . "</strong></div>";
            echo "<div class='code'>Server: " . htmlspecialchars($dbInfo['version']) . "</div>";
            
            // Check tables
            $tables = ['devices', 'versions', 'ota_logs'];
            echo "<h3>Tabellstatus:</h3>";
            foreach ($tables as $table) {
                try {
                    $stmt = $pdo->query("SHOW TABLES LIKE '{$table}'");
                    $exists = $stmt->fetch() !== false;
                    if ($exists) {
                        $countStmt = $pdo->query("SELECT COUNT(*) FROM `{$table}`");
                        $count = $countStmt->fetchColumn();
                        echo "<div class='success'>✓ {$table}: {$count} rader</div>";
                    } else {
                        echo "<div class='error'>✗ {$table}: Saknas</div>";
                    }
                } catch (PDOException $e) {
                    echo "<div class='error'>✗ {$table}: Fel - " . htmlspecialchars($e->getMessage()) . "</div>";
                }
            }
            
            // Check view
            try {
                $stmt = $pdo->query("SELECT COUNT(*) FROM information_schema.views WHERE table_name = 'device_overview' AND table_schema = DATABASE()");
                $viewExists = $stmt->fetchColumn() > 0;
                if ($viewExists) {
                    echo "<div class='success'>✓ device_overview vy: Finns</div>";
                } else {
                    echo "<div class='error'>✗ device_overview vy: Saknas</div>";
                }
            } catch (PDOException $e) {
                echo "<div class='error'>✗ device_overview vy: Fel - " . htmlspecialchars($e->getMessage()) . "</div>";
            }
            
        } else {
            echo "<div class='error'>❌ Kan inte ansluta till databasen</div>";
        }
    } catch (Exception $e) {
        echo "<div class='error'>❌ Databasfel: " . htmlspecialchars($e->getMessage()) . "</div>";
    }
    ?>
    
    <div class="code">
        <strong>Detaljerad status:</strong><br>
        <a href="db_status.php" target="_blank">db_status.php</a> - Visa JSON-formaterad status
    </div>

    <h2>Manuell installation</h2>
    <p>Om du föredrar att installera databasen manuellt, använd:</p>
    <div class="code">
        mysql -u ditt_användarnamn -p ditt_databasnamn < ota_database_schema.sql
    </div>

    <h2>Nästa steg</h2>
    <ol>
        <li>Skapa databastabeller (ovan)</li>
        <li>Lägg till exempeldata för testning (valfritt)</li>
        <li>Gå tillbaka till <a href="admin_dashboard.php">Admin Dashboard</a></li>
        <li>Kontrollera att alla funktioner fungerar</li>
    </ol>

    <div style="margin-top: 50px; text-align: center;">
        <a href="admin_dashboard.php">← Tillbaka till Dashboard</a> |
        <a href="db_status.php">Databasstatus</a> |
        <a href="admin_logout.php">Logga ut</a>
    </div>

</body>
</html>