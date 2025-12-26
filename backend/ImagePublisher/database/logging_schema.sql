-- PyRpiCamController Image Publisher Database Schema
-- This script creates the database structure for image publishing and logging

-- Table for camera log entries
CREATE TABLE IF NOT EXISTS Camlog (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cpuid VARCHAR(32) NOT NULL COMMENT 'Camera CPU ID/Serial',
    raw TEXT DEFAULT NULL COMMENT 'Raw JSON log data',
    logtime TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Server receive time',
    name VARCHAR(100) DEFAULT NULL COMMENT 'Logger name',
    levelname VARCHAR(20) DEFAULT NULL COMMENT 'Log level (DEBUG, INFO, WARNING, ERROR)',
    message TEXT DEFAULT NULL COMMENT 'Log message',
    created TIMESTAMP DEFAULT NULL COMMENT 'Original log creation time on device',
    INDEX idx_cpuid (cpuid),
    INDEX idx_logtime (logtime),
    INDEX idx_levelname (levelname),
    INDEX idx_created (created)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for image metadata (optional - for tracking uploaded images)
CREATE TABLE IF NOT EXISTS image_uploads (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cpuid VARCHAR(32) NOT NULL COMMENT 'Camera CPU ID/Serial',
    timestamp_key BIGINT NOT NULL COMMENT 'Image timestamp key',
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(500) NOT NULL COMMENT 'Relative path to stored image',
    thumb_path VARCHAR(500) DEFAULT NULL COMMENT 'Relative path to thumbnail',
    metadata_json TEXT DEFAULT NULL COMMENT 'Image metadata from camera',
    file_size BIGINT DEFAULT NULL COMMENT 'Image file size in bytes',
    image_width INT DEFAULT NULL,
    image_height INT DEFAULT NULL,
    INDEX idx_cpuid (cpuid),
    INDEX idx_timestamp (timestamp_key),
    INDEX idx_upload_time (upload_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert some sample data for testing
-- INSERT INTO Camlog (cpuid, name, levelname, message, created) VALUES 
-- ('test_cpu_001', 'CamController', 'INFO', 'System started successfully', NOW()),
-- ('test_cpu_001', 'CamController', 'DEBUG', 'Image captured: 1024x768', NOW()),
-- ('test_cpu_002', 'CamController', 'WARNING', 'Low disk space warning', NOW());