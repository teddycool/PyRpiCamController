-- PyRpiCamController OTA Database Schema
-- This script creates the database structure for managing OTA updates

-- Create database (if needed)
-- CREATE DATABASE pyrpicam_ota;
USE yobnhr6641_pycamota;

-- Table for device registration and management
CREATE TABLE IF NOT EXISTS devices (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for available software versions
CREATE TABLE IF NOT EXISTS versions (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for OTA update attempts and status tracking
CREATE TABLE IF NOT EXISTS ota_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    cpu_id VARCHAR(32) NOT NULL COMMENT 'For quick lookups',
    from_version VARCHAR(20) DEFAULT NULL,
    to_version VARCHAR(20) NOT NULL,
    git_tag VARCHAR(50) DEFAULT NULL COMMENT 'Git tag being updated to',
    git_commit_hash VARCHAR(40) DEFAULT NULL COMMENT 'Git commit hash being updated to',
    status ENUM('started', 'downloading', 'backing_up', 'installing', 'restarting_services', 'success', 'failed', 'rolled_back') NOT NULL,
    error_message TEXT DEFAULT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL DEFAULT NULL,
    duration_seconds INT DEFAULT NULL COMMENT 'Total update duration',
    download_size BIGINT DEFAULT NULL COMMENT 'Actual download size',
    backup_path VARCHAR(500) DEFAULT NULL COMMENT 'Path to system backup',
    services_restarted TEXT DEFAULT NULL COMMENT 'JSON array of services that were restarted',
    update_method ENUM('package', 'git_clone', 'git_pull') DEFAULT 'package',
    retry_count INT DEFAULT 0,
    ip_address VARCHAR(45) DEFAULT NULL COMMENT 'Client IP address',
    user_agent TEXT DEFAULT NULL COMMENT 'Client user agent',
    pre_update_checks_passed BOOLEAN DEFAULT TRUE,
    post_update_checks_passed BOOLEAN DEFAULT TRUE,
    rollback_reason TEXT DEFAULT NULL,
    INDEX idx_device_id (device_id),
    INDEX idx_cpu_id (cpu_id),
    INDEX idx_status (status),
    INDEX idx_git_tag (git_tag),
    INDEX idx_started_at (started_at),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for component-based versioning (Settings, Services, WebGui, etc.)
CREATE TABLE IF NOT EXISTS component_versions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    component_name ENUM('CamController', 'WebGui', 'Settings', 'Services', 'Updates') NOT NULL,
    current_version VARCHAR(20) NOT NULL,
    target_version VARCHAR(20) DEFAULT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    update_available BOOLEAN DEFAULT FALSE,
    update_priority ENUM('low', 'normal', 'high', 'critical') DEFAULT 'normal',
    notes TEXT DEFAULT NULL,
    UNIQUE KEY unique_device_component (device_id, component_name),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    INDEX idx_component_device (component_name, device_id),
    INDEX idx_update_available (update_available, component_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for available component releases
CREATE TABLE IF NOT EXISTS component_releases (
    id INT PRIMARY KEY AUTO_INCREMENT,
    component_name ENUM('CamController', 'WebGui', 'Settings', 'Services', 'Updates') NOT NULL,
    version VARCHAR(20) NOT NULL,
    release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_url VARCHAR(500) NOT NULL COMMENT 'URL to download this component version',
    checksum VARCHAR(64) NOT NULL COMMENT 'SHA256 checksum of the package',
    file_size BIGINT DEFAULT NULL COMMENT 'Package file size in bytes',
    requires_reboot BOOLEAN DEFAULT FALSE,
    requires_service_restart TEXT DEFAULT NULL COMMENT 'JSON array of services to restart',
    dependencies TEXT DEFAULT NULL COMMENT 'JSON object of component dependencies',
    update_groups TEXT DEFAULT NULL COMMENT 'JSON array: Which groups can receive this update',
    min_version VARCHAR(20) DEFAULT NULL COMMENT 'Minimum version required for this update',
    max_version VARCHAR(20) DEFAULT NULL COMMENT 'Maximum version this can update from',
    release_notes TEXT DEFAULT NULL,
    status ENUM('development', 'testing', 'stable', 'deprecated') DEFAULT 'development',
    created_by VARCHAR(100) DEFAULT NULL,
    UNIQUE KEY unique_component_version (component_name, version),
    INDEX idx_component_status (component_name, status),
    INDEX idx_release_date (release_date),
    INDEX idx_version_status (version, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for component update logs
CREATE TABLE IF NOT EXISTS component_update_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    cpu_id VARCHAR(32) NOT NULL,
    component_name ENUM('CamController', 'WebGui', 'Settings', 'Services', 'Updates') NOT NULL,
    from_version VARCHAR(20) DEFAULT NULL,
    to_version VARCHAR(20) NOT NULL,
    status ENUM('started', 'downloading', 'installing', 'success', 'failed', 'rolled_back') NOT NULL,
    error_message TEXT DEFAULT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL DEFAULT NULL,
    duration_seconds INT DEFAULT NULL,
    download_size BIGINT DEFAULT NULL,
    retry_count INT DEFAULT 0,
    services_restarted TEXT DEFAULT NULL COMMENT 'JSON array of services that were restarted',
    backup_path VARCHAR(500) DEFAULT NULL COMMENT 'Path to backup of previous version',
    ip_address VARCHAR(45) DEFAULT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    INDEX idx_device_component (device_id, component_name),
    INDEX idx_status_component (status, component_name),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for device configuration and settings
CREATE TABLE IF NOT EXISTS device_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT DEFAULT NULL COMMENT 'JSON string for configuration values',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by VARCHAR(100) DEFAULT NULL,
    UNIQUE KEY unique_device_config (device_id, config_key),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    INDEX idx_device_key (device_id, config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for device health and statistics
CREATE TABLE IF NOT EXISTS device_stats (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    cpu_id VARCHAR(32) NOT NULL,
    uptime_seconds BIGINT DEFAULT NULL,
    cpu_temperature DECIMAL(5,2) DEFAULT NULL,
    memory_usage_mb INT DEFAULT NULL,
    disk_usage_gb DECIMAL(8,2) DEFAULT NULL,
    network_status VARCHAR(50) DEFAULT NULL,
    camera_status VARCHAR(50) DEFAULT NULL,
    last_image_time TIMESTAMP NULL DEFAULT NULL,
    error_count INT DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id),
    INDEX idx_recorded_at (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert sample system releases with git integration
INSERT INTO versions (version, git_tag, git_commit_hash, download_url, git_clone_url, checksum, services_to_restart, requires_reboot, update_groups, release_notes, changelog, status, backup_required, update_script) VALUES
('1.0.0', 'v1.0.0', 'a1b2c3d4e5f6789012345678901234567890abcd', 'https://example.com/releases/PyRpiCamController_v1.0.0.tar.gz', 'https://github.com/teddycool/PyRpiCamController.git', 'a1b2c3d4e5f6...', '["camcontroller.service", "camcontroller-web.service", "camcontroller-update.service"]', FALSE, '["production", "beta", "dev"]', 'Initial stable release with all core features', 'Initial release with CamController, WebGui, Settings, Services, and Updates systems', 'stable', TRUE, 'install-all.py'),
('1.0.1', 'v1.0.1', 'b2c3d4e5f6a1789012345678901234567890bcde', 'https://example.com/releases/PyRpiCamController_v1.0.1.tar.gz', 'https://github.com/teddycool/PyRpiCamController.git', 'b2c3d4e5f6a1...', '["camcontroller.service", "camcontroller-web.service"]', FALSE, '["beta", "dev"]', 'Bug fixes and improvements', 'Fixed camera initialization issues\nImproved web interface responsiveness\nUpdated settings schema', 'testing', TRUE, 'update-system.py'),
('1.1.0', 'v1.1.0', 'c3d4e5f6a1b2789012345678901234567890cdef', 'https://example.com/releases/PyRpiCamController_v1.1.0.tar.gz', 'https://github.com/teddycool/PyRpiCamController.git', 'c3d4e5f6a1b2...', '["camcontroller.service", "camcontroller-web.service", "camcontroller-update.service", "smbd"]', TRUE, '["dev"]', 'Major feature update with enhanced OTA system and new camera features', 'New motion detection algorithms\nEnhanced OTA update system with rollback\nImproved Samba integration\nNew web interface features', 'development', TRUE, 'major-update.py');

-- Insert sample device (replace with your actual device data)
INSERT INTO devices (cpu_id, api_key, device_name, location, current_version, update_group) VALUES
('1234567890abcdef', 'dev-key-12345-abcdef-67890', 'Test Camera 1', 'Development Lab', '1.0.0', 'dev'),
('abcdef1234567890', 'prod-key-abcdef-12345-67890', 'Production Camera 1', 'Main Office', '1.0.0', 'production');

-- Create views for common queries
CREATE VIEW device_overview AS
SELECT 
    d.id,
    d.cpu_id,
    d.device_name,
    d.location,
    d.current_version,
    d.target_version,
    d.status,
    d.update_enabled,
    d.update_group,
    d.last_seen,
    TIMESTAMPDIFF(MINUTE, d.last_seen, NOW()) as minutes_since_last_seen,
    (SELECT COUNT(*) FROM ota_logs ol WHERE ol.device_id = d.id AND ol.status = 'failed' AND ol.started_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)) as failed_updates_24h,
    (SELECT COUNT(*) FROM ota_logs ol WHERE ol.device_id = d.id AND ol.status = 'success' AND ol.completed_at > DATE_SUB(NOW(), INTERVAL 30 DAY)) as successful_updates_30d
FROM devices d;

-- Create view for update statistics
CREATE VIEW update_statistics AS
SELECT 
    v.version,
    v.status as version_status,
    v.release_date,
    COUNT(ol.id) as total_attempts,
    SUM(CASE WHEN ol.status = 'success' THEN 1 ELSE 0 END) as successful_updates,
    SUM(CASE WHEN ol.status = 'failed' THEN 1 ELSE 0 END) as failed_updates,
    SUM(CASE WHEN ol.status = 'rolled_back' THEN 1 ELSE 0 END) as rolled_back_updates,
    ROUND(AVG(ol.duration_seconds), 2) as avg_duration_seconds,
    COUNT(DISTINCT ol.device_id) as unique_devices_updated
FROM versions v
LEFT JOIN ota_logs ol ON v.version = ol.to_version
GROUP BY v.id, v.version, v.status, v.release_date;

-- Performance optimization: Add partitioning for large log tables (optional)
-- ALTER TABLE ota_logs PARTITION BY RANGE (YEAR(started_at)) (
--     PARTITION p2023 VALUES LESS THAN (2024),
--     PARTITION p2024 VALUES LESS THAN (2025),
--     PARTITION p2025 VALUES LESS THAN (2026),
--     PARTITION p_future VALUES LESS THAN MAXVALUE
-- );

-- Create indexes for better performance
CREATE INDEX idx_ota_logs_composite ON ota_logs (device_id, status, started_at);
CREATE INDEX idx_devices_last_seen ON devices (last_seen, status);
CREATE INDEX idx_device_stats_recent ON device_stats (device_id, recorded_at);

DELIMITER //

-- Stored procedure to get next update for a device
CREATE PROCEDURE GetDeviceUpdate(IN p_cpu_id VARCHAR(32), IN p_api_key VARCHAR(64))
BEGIN
    DECLARE v_device_id INT;
    DECLARE v_current_version VARCHAR(20);
    DECLARE v_update_group VARCHAR(50);
    DECLARE v_update_enabled BOOLEAN;
    
    -- Validate device and API key
    SELECT id, current_version, update_group, update_enabled
    INTO v_device_id, v_current_version, v_update_group, v_update_enabled
    FROM devices 
    WHERE cpu_id = p_cpu_id AND api_key = p_api_key AND status = 'active';
    
    IF v_device_id IS NULL THEN
        SELECT 'INVALID_DEVICE' as error;
    ELSEIF v_update_enabled = FALSE THEN
        SELECT 'UPDATES_DISABLED' as error;
    ELSE
        -- Update last_seen
        UPDATE devices SET last_seen = NOW() WHERE id = v_device_id;
        
        -- Find next available version
        SELECT 
            v.version,
            v.git_tag,
            v.git_commit_hash,
            v.download_url,
            v.git_clone_url,
            v.checksum,
            v.file_size,
            v.requires_reboot,
            v.services_to_restart,
            v.release_notes,
            v.changelog,
            v.backup_required,
            v.update_script,
            v.pre_update_checks,
            v.post_update_checks,
            CASE WHEN v.version != v_current_version THEN TRUE ELSE FALSE END as update_available
        FROM versions v
        WHERE v.status = 'stable'
        AND (v.update_groups IS NULL OR v.update_groups LIKE CONCAT('%"', v_update_group, '"%'))
        AND (v.min_version IS NULL OR v_current_version >= v.min_version)
        AND (v.max_version IS NULL OR v_current_version <= v.max_version)
        ORDER BY v.release_date DESC
        LIMIT 1;
    END IF;
END //

-- Stored procedure to log OTA status for full system updates
CREATE PROCEDURE GetDeviceUpdate(IN p_cpu_id VARCHAR(32), IN p_api_key VARCHAR(64))
BEGIN
    DECLARE v_device_id INT;
    DECLARE v_current_version VARCHAR(20);
    DECLARE v_update_group VARCHAR(50);
    DECLARE v_update_enabled BOOLEAN;
    
    -- Validate device and API key
    SELECT id, current_version, update_group, update_enabled
    INTO v_device_id, v_current_version, v_update_group, v_update_enabled
    FROM devices 
    WHERE cpu_id = p_cpu_id AND api_key = p_api_key AND status = 'active';
    
    IF v_device_id IS NULL THEN
        SELECT 'INVALID_DEVICE' as error;
    ELSEIF v_update_enabled = FALSE THEN
        SELECT 'UPDATES_DISABLED' as error;
    ELSE
        -- Update last_seen
        UPDATE devices SET last_seen = NOW() WHERE id = v_device_id;
        
        -- Find next available version
        SELECT 
            v.version,
            v.download_url,
            v.checksum,
            v.file_size,
            v.requires_reboot,
            v.release_notes,
            CASE WHEN v.version != v_current_version THEN TRUE ELSE FALSE END as update_available
        FROM versions v
        WHERE v.status = 'stable'
        AND (v.update_groups IS NULL OR v.update_groups LIKE CONCAT('%"', v_update_group, '"%'))
        AND (v.min_version IS NULL OR v_current_version >= v.min_version)
        AND (v.max_version IS NULL OR v_current_version <= v.max_version)
        ORDER BY v.release_date DESC
        LIMIT 1;
    END IF;
END //

-- Stored procedure to log OTA status
CREATE PROCEDURE LogOTAStatus(
    IN p_cpu_id VARCHAR(32),
    IN p_api_key VARCHAR(64),
    IN p_from_version VARCHAR(20),
    IN p_to_version VARCHAR(20),
    IN p_git_tag VARCHAR(50),
    IN p_git_commit_hash VARCHAR(40),
    IN p_status VARCHAR(30),
    IN p_error_message TEXT,
    IN p_backup_path VARCHAR(500),
    IN p_services_restarted TEXT,
    IN p_update_method VARCHAR(20),
    IN p_ip_address VARCHAR(45)
)
BEGIN
    DECLARE v_device_id INT;
    DECLARE v_log_id INT;
    
    -- Validate device
    SELECT id INTO v_device_id 
    FROM devices 
    WHERE cpu_id = p_cpu_id AND api_key = p_api_key;
    
    IF v_device_id IS NOT NULL THEN
        -- Check if there's an ongoing update to complete
        SELECT id INTO v_log_id
        FROM ota_logs 
        WHERE device_id = v_device_id 
        AND to_version = p_to_version 
        AND status IN ('started', 'downloading', 'backing_up', 'installing', 'restarting_services')
        ORDER BY started_at DESC
        LIMIT 1;
        
        IF v_log_id IS NOT NULL AND p_status IN ('success', 'failed', 'rolled_back') THEN
            -- Complete existing log entry
            UPDATE ota_logs SET
                status = p_status,
                error_message = p_error_message,
                backup_path = p_backup_path,
                services_restarted = p_services_restarted,
                completed_at = NOW(),
                duration_seconds = TIMESTAMPDIFF(SECOND, started_at, NOW()),
                rollback_reason = CASE WHEN p_status = 'rolled_back' THEN p_error_message ELSE NULL END
            WHERE id = v_log_id;
            
            -- Update device current version if successful
            IF p_status = 'success' THEN
                UPDATE devices SET current_version = p_to_version WHERE id = v_device_id;
            END IF;
        ELSE
            -- Create new log entry
            INSERT INTO ota_logs (
                device_id, cpu_id, from_version, to_version, git_tag, git_commit_hash,
                status, error_message, backup_path, services_restarted, update_method, ip_address
            )
            VALUES (
                v_device_id, p_cpu_id, p_from_version, p_to_version, p_git_tag, p_git_commit_hash,
                p_status, p_error_message, p_backup_path, p_services_restarted, p_update_method, p_ip_address
            );
        END IF;
        
        -- Update device last_seen
        UPDATE devices SET last_seen = NOW() WHERE id = v_device_id;
    END IF;
END //

DELIMITER ;

-- Grant appropriate permissions (adjust as needed for your setup)
-- CREATE USER 'ota_user'@'localhost' IDENTIFIED BY 'secure_password_here';
-- GRANT SELECT, INSERT, UPDATE ON pyrpicam_ota.* TO 'ota_user'@'localhost';
-- FLUSH PRIVILEGES;

-- Show table information
SHOW TABLES;
SELECT 'Database schema created successfully!' as status;