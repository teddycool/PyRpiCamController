<?php
/**
 * Shared helpers: HTTP responses, authentication, input sanitisation.
 */

require_once __DIR__ . '/config.php';

// ---------------------------------------------------------------------------
// HTTP / JSON helpers
// ---------------------------------------------------------------------------

/**
 * Send a JSON success response and exit.
 *
 * @param mixed $data
 * @param int   $status HTTP status code
 */
function json_ok($data = [], int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/**
 * Send a JSON error response and exit.
 *
 * @param string $message Human-readable error
 * @param int    $status  HTTP status code
 */
function json_error(string $message, int $status = 400): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Decode the request body as JSON.  Exits with 400 on parse failure.
 *
 * @return array
 */
function json_body(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === false || $raw === '') {
        return [];
    }
    $data = json_decode($raw, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        json_error('Invalid JSON body: ' . json_last_error_msg());
    }
    return $data;
}

/**
 * Enforce that the request method matches; exit 405 otherwise.
 */
function require_method(string ...$methods): void
{
    if (!in_array($_SERVER['REQUEST_METHOD'], $methods, true)) {
        header('Allow: ' . implode(', ', $methods));
        json_error('Method not allowed', 405);
    }
}

// ---------------------------------------------------------------------------
// Device authentication
// ---------------------------------------------------------------------------

/**
 * Authenticate a device request.
 *
 * Accepts credentials from:
 *   - GET query params  cpu_id / api_key
 *   - POST JSON body    cpu_id / api_key
 *
 * On success, returns the cam_devices row.
 * On failure, exits with 401.
 *
 * Side-effect: updates last_seen and last_ip on every successful auth.
 *
 * @return array cam_devices row
 */
function authenticate_device(): array
{
    // Collect from either GET or decoded JSON body (already read elsewhere if needed)
    $cpu_id  = $_GET['cpu_id']  ?? null;
    $api_key = $_GET['api_key'] ?? null;

    if ($cpu_id === null || $api_key === null) {
        // Try JSON body (POST)
        $body    = json_body();
        $cpu_id  = $body['cpu_id']  ?? null;
        $api_key = $body['api_key'] ?? null;
    }

    if (!$cpu_id || !$api_key) {
        json_error('Missing cpu_id or api_key', 401);
    }

    try {
        $pdo  = cam_db();
        $stmt = $pdo->prepare(
            'SELECT * FROM cam_devices WHERE device_id = ? AND api_key = ? AND is_active = 1'
        );
        $stmt->execute([$cpu_id, $api_key]);
        $device = $stmt->fetch();
    } catch (Exception $e) {
        json_error('Database error', 500);
    }

    if (!$device) {
        json_error('Invalid device credentials', 401);
    }

    // Update last_seen / last_ip (best-effort)
    try {
        $ip = $_SERVER['REMOTE_ADDR'] ?? null;
        $pdo->prepare('UPDATE cam_devices SET last_seen = NOW(), last_ip = ? WHERE id = ?')
            ->execute([$ip, $device['id']]);
    } catch (Exception $e) {
        // Non-fatal
    }

    return $device;
}

// ---------------------------------------------------------------------------
// Admin session authentication
// ---------------------------------------------------------------------------

/**
 * Ensure the current session belongs to a valid admin.
 * If not, redirect to login and exit.
 */
function require_admin_session(): void
{
    if (session_status() === PHP_SESSION_NONE) {
        session_name(CAM_SESSION_NAME);
        session_start();
    }
    if (empty($_SESSION['admin_id'])) {
        header('Location: admin_login.php');
        exit;
    }
}

/**
 * Return the logged-in admin row, or null if not authenticated.
 *
 * @return array|null
 */
function current_admin(): ?array
{
    if (session_status() === PHP_SESSION_NONE) {
        session_name(CAM_SESSION_NAME);
        session_start();
    }
    if (empty($_SESSION['admin_id'])) {
        return null;
    }
    try {
        $stmt = cam_db()->prepare('SELECT id, username, email FROM cam_admins WHERE id = ? AND is_active = 1');
        $stmt->execute([$_SESSION['admin_id']]);
        return $stmt->fetch() ?: null;
    } catch (Exception $e) {
        return null;
    }
}

// ---------------------------------------------------------------------------
// Admin JSON API authentication (Bearer token = session cookie)
// ---------------------------------------------------------------------------

/**
 * For admin API endpoints called via AJAX.
 * Exits 401 if session is not valid.
 */
function require_admin_api(): void
{
    if (session_status() === PHP_SESSION_NONE) {
        session_name(CAM_SESSION_NAME);
        session_start();
    }
    if (empty($_SESSION['admin_id'])) {
        json_error('Unauthenticated', 401);
    }
}

// ---------------------------------------------------------------------------
// Misc utilities
// ---------------------------------------------------------------------------

/**
 * Compute SHA-256 hex digest of a file.
 */
function sha256_file(string $path): string
{
    return hash_file('sha256', $path);
}

/**
 * Generate a cryptographically random API key.
 */
function generate_api_key(): string
{
    return bin2hex(random_bytes(32)); // 64 hex chars
}

/**
 * Compare semantic versions.  Returns -1, 0, or 1.
 */
function version_compare_sem(string $a, string $b): int
{
    return version_compare($a, $b);
}
