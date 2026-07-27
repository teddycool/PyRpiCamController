-- =============================================================================
-- PyRpiCamController OTA Backend Schema v2
-- Database: yobnhr6641_pycamota (sensorwebben.se)
-- Prefix: cam_ — isolates cam tables from other products in the same DB
-- =============================================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;


-- -----------------------------------------------------------------------------
-- cam_admins
-- Web-UI login accounts for the admin dashboard.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cam_admins (
    id           INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    username     VARCHAR(64)     NOT NULL,
    password_hash VARCHAR(255)   NOT NULL,           -- bcrypt
    email        VARCHAR(255)    DEFAULT NULL,
    is_active    TINYINT(1)      NOT NULL DEFAULT 1,
    last_login   DATETIME        DEFAULT NULL,
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cam_admins_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- cam_devices
-- One row per registered Pi device.
-- api_key is the shared secret sent in every OTA check request.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cam_devices (
    id               INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    device_id        VARCHAR(64)     NOT NULL,        -- hardware serial / UUID
    api_key          VARCHAR(128)    NOT NULL,        -- SHA-256 hex, generated on registration
    name             VARCHAR(128)    DEFAULT NULL,    -- human-readable label
    current_version  VARCHAR(32)     DEFAULT NULL,    -- last version reported by device
    channel          VARCHAR(32)     NOT NULL DEFAULT 'stable',  -- stable | testing | beta
    is_active        TINYINT(1)      NOT NULL DEFAULT 1,
    last_seen        DATETIME        DEFAULT NULL,
    last_ip          VARCHAR(45)     DEFAULT NULL,    -- IPv4 or IPv6
    notes            TEXT            DEFAULT NULL,
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cam_devices_device_id (device_id),
    UNIQUE KEY uq_cam_devices_api_key (api_key),
    INDEX idx_cam_devices_channel (channel),
    INDEX idx_cam_devices_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- cam_releases
-- One row per published release package (.tar.gz).
-- status lifecycle: draft → testing → stable → deprecated
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cam_releases (
    id               INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    version          VARCHAR(32)     NOT NULL,        -- e.g. "1.0.3"
    channel          VARCHAR(32)     NOT NULL DEFAULT 'stable',
    status           ENUM('draft','testing','stable','deprecated')
                                     NOT NULL DEFAULT 'draft',
    filename         VARCHAR(255)    NOT NULL,        -- basename stored under releases/
    filesize         INT UNSIGNED    NOT NULL DEFAULT 0,  -- bytes
    checksum_sha256  CHAR(64)        NOT NULL,
    min_version      VARCHAR(32)     DEFAULT NULL,    -- NULL = allow all upgrades
    release_notes    TEXT            DEFAULT NULL,
    uploaded_by      INT UNSIGNED    DEFAULT NULL,    -- FK → cam_admins.id
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cam_releases_version_channel (version, channel),
    INDEX idx_cam_releases_status (status),
    INDEX idx_cam_releases_channel_status (channel, status),
    CONSTRAINT fk_cam_releases_admin
        FOREIGN KEY (uploaded_by) REFERENCES cam_admins (id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- cam_ota_logs
-- Immutable event log: every check and every install attempt.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cam_ota_logs (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_id        VARCHAR(64)     NOT NULL,        -- denormalised for fast lookup even if device deleted
    event_type       ENUM('check','download_start','install_ok','install_fail','rollback')
                                     NOT NULL,
    from_version     VARCHAR(32)     DEFAULT NULL,
    to_version       VARCHAR(32)     DEFAULT NULL,
    release_id       INT UNSIGNED    DEFAULT NULL,    -- FK → cam_releases.id (nullable)
    success          TINYINT(1)      DEFAULT NULL,    -- NULL = informational, 1 = ok, 0 = fail
    message          TEXT            DEFAULT NULL,    -- error text or "no update available"
    client_ip        VARCHAR(45)     DEFAULT NULL,
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_cam_ota_logs_device_id (device_id),
    INDEX idx_cam_ota_logs_event_type (event_type),
    INDEX idx_cam_ota_logs_created_at (created_at),
    CONSTRAINT fk_cam_ota_logs_release
        FOREIGN KEY (release_id) REFERENCES cam_releases (id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- Bootstrap: default admin account
-- Password: changeme  (bcrypt cost 12 — CHANGE BEFORE DEPLOYING)
-- =============================================================================
INSERT IGNORE INTO cam_admins (username, password_hash, email)
VALUES (
    'admin',
    '$2y$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
    NULL
);
