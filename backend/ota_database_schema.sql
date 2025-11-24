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
    status ENUM('started', 'downloading', 'installing', 'success', 'failed', 'rolled_back') NOT NULL,
    error_message TEXT DEFAULT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL DEFAULT NULL,
    duration_seconds INT DEFAULT NULL COMMENT 'Total update duration',
    download_size BIGINT DEFAULT NULL COMMENT 'Actual download size',
    retry_count INT DEFAULT 0,
    ip_address VARCHAR(45) DEFAULT NULL COMMENT 'Client IP address',
    user_agent TEXT DEFAULT NULL COMMENT 'Client user agent',
    INDEX idx_device_id (device_id),
    INDEX idx_cpu_id (cpu_id),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
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

-- Insert some sample data for testing
INSERT INTO versions (version, download_url, checksum, requires_reboot, update_groups, release_notes, status) VALUES
('1.0.0', 'https://example.com/releases/pycam_v1.0.0.tar.gz', 'a1b2c3d4e5f6...', FALSE, '["production", "beta", "dev"]', 'Initial release', 'stable'),
('1.0.1', 'https://example.com/releases/pycam_v1.0.1.tar.gz', 'b2c3d4e5f6a1...', FALSE, '["beta", "dev"]', 'Bug fixes and improvements', 'testing'),
('1.1.0', 'https://example.com/releases/pycam_v1.1.0.tar.gz', 'c3d4e5f6a1b2...', TRUE, '["dev"]', 'Major feature update with OTA system', 'development');

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
    IN p_status VARCHAR(20),
    IN p_error_message TEXT,
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
        AND status IN ('started', 'downloading', 'installing')
        ORDER BY started_at DESC
        LIMIT 1;
        
        IF v_log_id IS NOT NULL AND p_status IN ('success', 'failed', 'rolled_back') THEN
            -- Complete existing log entry
            UPDATE ota_logs SET
                status = p_status,
                error_message = p_error_message,
                completed_at = NOW(),
                duration_seconds = TIMESTAMPDIFF(SECOND, started_at, NOW())
            WHERE id = v_log_id;
            
            -- Update device current version if successful
            IF p_status = 'success' THEN
                UPDATE devices SET current_version = p_to_version WHERE id = v_device_id;
            END IF;
        ELSE
            -- Create new log entry
            INSERT INTO ota_logs (device_id, cpu_id, from_version, to_version, status, error_message, ip_address)
            VALUES (v_device_id, p_cpu_id, p_from_version, p_to_version, p_status, p_error_message, p_ip_address);
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