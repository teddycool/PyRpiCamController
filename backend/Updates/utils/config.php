<?php
/**
 * Database connection and application constants.
 *
 * Secrets (DB credentials) are loaded from a file OUTSIDE the web root:
 *   /home/<user>/private/cam_ota_secrets.php
 *
 * That file must define:
 *   define('CAM_DB_HOST', 'localhost');
 *   define('CAM_DB_NAME', 'yobnhr6641_pycamota');
 *   define('CAM_DB_USER', 'yobnhr6641_pycamota');
 *   define('CAM_DB_PASS', 'your-password-here');
 *
 * If the secrets file does not exist, fallback constants are used (dev only).
 */

$secretsFile = dirname(__DIR__, 4) . '/private/cam_ota_secrets.php';
if (file_exists($secretsFile)) {
    require_once $secretsFile;
} else {
    // Dev fallback — override in secrets file on production
    define('CAM_DB_HOST', 'localhost');
    define('CAM_DB_NAME', 'yobnhr6641_pycamota');
    define('CAM_DB_USER', 'yobnhr6641_pycamota');
    define('CAM_DB_PASS', '');
}

// Base URL of this backend (no trailing slash)
define('CAM_BASE_URL', 'https://www.sensorwebben.se/pycamota');

// Directory where release tarballs are stored (absolute, writable by web server)
define('CAM_RELEASES_DIR', dirname(__DIR__) . '/releases');

// Public URL prefix for downloading releases
define('CAM_RELEASES_URL', CAM_BASE_URL . '/releases');

// Maximum upload size for release packages (bytes) — 50 MB
define('CAM_MAX_UPLOAD_BYTES', 50 * 1024 * 1024);

// Session name (avoids collisions with other apps on the same domain)
define('CAM_SESSION_NAME', 'cam_ota_admin');

// Timezone for all timestamps
date_default_timezone_set('UTC');

/**
 * Return a singleton PDO connection.
 *
 * @throws RuntimeException on connection failure
 */
function cam_db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $dsn = 'mysql:host=' . CAM_DB_HOST . ';dbname=' . CAM_DB_NAME . ';charset=utf8mb4';
        $options = [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ];
        $pdo = new PDO($dsn, CAM_DB_USER, CAM_DB_PASS, $options);
    }
    return $pdo;
}
