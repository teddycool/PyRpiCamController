<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

require_once 'admin_auth.php';

// Perform logout
admin_logout();

// Redirect to login page
header('Location: admin_login.php?message=logged_out');
exit;
?>