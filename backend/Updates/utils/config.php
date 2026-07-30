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

$secretsCandidates = [
    getenv('CAM_SECRETS_FILE') ?: '',
    __DIR__ . '/cam_ota_secrets.php',             // utils/ — blocked from HTTP by .htaccess
    dirname(__DIR__, 3) . '/private/cam_ota_secrets.php',
    dirname(__DIR__, 4) . '/private/cam_ota_secrets.php',
];

$secretsFile = '';
foreach ($secretsCandidates as $candidate) {
    if ($candidate && file_exists($candidate)) {
        $secretsFile = $candidate;
        break;
    }
}

if ($secretsFile) {
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

// PHP 8.0+ session cookie settings (strict SameSite for security)
if (PHP_VERSION_ID >= 80000) {
    ini_set('session.cookie_samesite', 'Lax');
    ini_set('session.cookie_httponly', '1');
    ini_set('session.cookie_secure', empty($_SERVER['HTTPS']) ? '0' : '1');
}

// Error logging for debugging (logs to PHP error log, not displayed to users)
ini_set('log_errors', '1');
error_reporting(E_ALL);

/**
 * Return a singleton PDO connection.
 * PHP 8.3 compatible with fallback for shared hosting with limited charset support.
 *
 * @throws RuntimeException on connection failure
 */
function cam_db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        try {
            // Try with utf8mb4 first (recommended)
            $dsn = 'mysql:host=' . CAM_DB_HOST . ';dbname=' . CAM_DB_NAME . ';charset=utf8mb4';
            $options = [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
            ];
            $pdo = new PDO($dsn, CAM_DB_USER, CAM_DB_PASS, $options);
        } catch (PDOException $e) {
            if (strpos($e->getMessage(), 'utf8mb4') !== false || 
                strpos($e->getMessage(), 'character set') !== false) {
                // Fallback: Try without charset in DSN (let server auto-detect)
                // This works on shared hosting with limited charset support
                try {
                    $dsn = 'mysql:host=' . CAM_DB_HOST . ';dbname=' . CAM_DB_NAME;
                    $pdo = new PDO($dsn, CAM_DB_USER, CAM_DB_PASS, $options);
                    error_log('PDO: Connected with server default charset (utf8mb4 unavailable)');
                } catch (PDOException $e2) {
                    error_log('PDO Connection Error: ' . $e2->getMessage() . ' Code: ' . $e2->getCode());
                    throw new RuntimeException('Database connection failed. Check error log.');
                }
            } else {
                error_log('PDO Connection Error: ' . $e->getMessage() . ' Code: ' . $e->getCode());
                throw new RuntimeException('Database connection failed. Check error log.');
            }
        }
    }
    return $pdo;
}
