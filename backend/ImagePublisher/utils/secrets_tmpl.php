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

// Database configuration for Image Publisher system
define('DB_HOST', 'localhost');
define('DB_NAME', 'your_database_name_here');
define('DB_USER', 'your_database_user_here');
define('DB_PASS', 'your_secure_database_password_here');
define('DB_CHARSET', 'utf8mb4');

// API Security (optional - for future authentication features)
define('API_SECRET_KEY', 'your_api_secret_key_here');
define('DEVICE_AUTH_KEY', 'your_device_auth_key_here'); // For validating camera uploads

// File Upload Security
define('UPLOAD_SECRET', 'your_upload_secret_here'); // For validating file uploads
define('MAX_UPLOAD_SIZE', 10485760); // 10MB in bytes

?>