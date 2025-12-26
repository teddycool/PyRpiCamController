<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

/**
 * Admin Authentication System
 * 
 * Provides authentication functions for the OTA admin dashboard.
 */

require_once '../utils/config.php';

// Start session with secure settings
function start_admin_session() {
    // Configure secure session settings
    ini_set('session.cookie_httponly', 1);
    ini_set('session.cookie_secure', REQUIRE_HTTPS ? 1 : 0);
    ini_set('session.use_strict_mode', 1);
    ini_set('session.cookie_samesite', 'Strict');
    
    session_name(ADMIN_SESSION_NAME);
    
    if (session_status() === PHP_SESSION_NONE) {
        session_start();
    }
    
    // Regenerate session ID periodically for security
    if (!isset($_SESSION['last_regeneration'])) {
        $_SESSION['last_regeneration'] = time();
    } else if (time() - $_SESSION['last_regeneration'] > 300) { // 5 minutes
        session_regenerate_id(true);
        $_SESSION['last_regeneration'] = time();
    }
}

// Check if user is authenticated
function is_admin_authenticated() {
    start_admin_session();
    
    if (!isset($_SESSION['admin_authenticated']) || !$_SESSION['admin_authenticated']) {
        return false;
    }
    
    // Check session timeout
    if (isset($_SESSION['admin_last_activity']) && 
        (time() - $_SESSION['admin_last_activity']) > ADMIN_SESSION_TIMEOUT) {
        admin_logout();
        return false;
    }
    
    // Update last activity
    $_SESSION['admin_last_activity'] = time();
    return true;
}

// Authenticate admin user
function authenticate_admin($username, $password) {
    if ($username === ADMIN_USERNAME && password_verify($password, ADMIN_PASSWORD_HASH)) {
        start_admin_session();
        $_SESSION['admin_authenticated'] = true;
        $_SESSION['admin_username'] = $username;
        $_SESSION['admin_login_time'] = time();
        $_SESSION['admin_last_activity'] = time();
        
        // Log successful login
        error_log("Admin login successful for user: " . $username . " from IP: " . get_client_ip());
        return true;
    } else {
        // Log failed login attempt
        error_log("Admin login failed for user: " . $username . " from IP: " . get_client_ip());
        return false;
    }
}

// Logout admin user
function admin_logout() {
    start_admin_session();
    
    // Log logout
    if (isset($_SESSION['admin_username'])) {
        error_log("Admin logout for user: " . $_SESSION['admin_username'] . " from IP: " . get_client_ip());
    }
    
    // Clear all session data
    $_SESSION = [];
    
    // Destroy session cookie
    if (ini_get("session.use_cookies")) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000,
            $params["path"], $params["domain"],
            $params["secure"], $params["httponly"]
        );
    }
    
    // Destroy session
    session_destroy();
}

// Require admin authentication (redirect if not authenticated)
function require_admin_auth() {
    if (!is_admin_authenticated()) {
        // For AJAX requests, return JSON error
        if (!empty($_SERVER['HTTP_X_REQUESTED_WITH']) && 
            strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest') {
            http_response_code(401);
            die(json_encode(['error' => 'Authentication required']));
        }
        
        // For regular requests, redirect to login
        header('Location: admin_login.php');
        exit;
    }
}

// Get client IP address
function get_client_ip() {
    $ip_keys = ['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'HTTP_CLIENT_IP', 'REMOTE_ADDR'];
    
    foreach ($ip_keys as $key) {
        if (array_key_exists($key, $_SERVER) === true) {
            $ip = $_SERVER[$key];
            if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
                return $ip;
            }
        }
    }
    
    return $_SERVER['REMOTE_ADDR'] ?? 'unknown';
}

// Rate limiting for login attempts
function check_login_rate_limit($ip) {
    $rate_limit_file = sys_get_temp_dir() . '/ota_login_attempts_' . md5($ip);
    $max_attempts = 5;
    $window = 900; // 15 minutes
    
    if (file_exists($rate_limit_file)) {
        $attempts = json_decode(file_get_contents($rate_limit_file), true);
        
        // Clean old attempts
        $attempts = array_filter($attempts, function($time) use ($window) {
            return (time() - $time) < $window;
        });
        
        if (count($attempts) >= $max_attempts) {
            return false;
        }
    } else {
        $attempts = [];
    }
    
    // Add current attempt
    $attempts[] = time();
    file_put_contents($rate_limit_file, json_encode($attempts));
    
    return true;
}

// Generate CSRF token
function generate_csrf_token() {
    start_admin_session();
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

// Verify CSRF token
function verify_csrf_token($token) {
    start_admin_session();
    return isset($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $token);
}
?>