<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

// INSTRUCTIONS:
// 1. Copy this file to secrets.php
// 2. Update all the configuration values below
// 3. The secrets.php file is git-ignored and will not be committed


// Database configuration
define('DB_HOST', 'localhost');
define('DB_NAME', 'your_database_name_here');
define('DB_USER', 'your_database_user_here');
define('DB_PASS', 'your_secure_database_password_here');
define('DB_CHARSET', 'utf8mb4');

// Admin authentication - CHANGE THESE DEFAULTS!
define('ADMIN_USERNAME', 'admin'); // Change this to your preferred admin username
define('ADMIN_PASSWORD_HASH', password_hash('your_strong_admin_password_here', PASSWORD_DEFAULT)); // Set your admin password
define('ADMIN_SESSION_TIMEOUT', 3600); // Session timeout in seconds (3600 = 1 hour)
define('ADMIN_SESSION_NAME', 'pycamota_admin'); // Session name

// API Keys and Security
define('API_SECRET_KEY', 'your_api_secret_key_here'); // For API authentication
define('ENCRYPTION_KEY', 'your_encryption_key_here'); // For data encryption if needed

?>
