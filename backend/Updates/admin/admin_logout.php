<?php
require_once __DIR__ . '/../utils/config.php';
session_name(CAM_SESSION_NAME);
session_start();
$_SESSION = [];
session_destroy();
header('Location: admin_login.php');
exit;
