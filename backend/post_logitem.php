<?php
/*
 This file is an example of a backend receiving-script for log-items that is stored in a datbase table.
 
*/
// This script is called from the PyCam software when a log-item is created.
//TODO: check valid cpuid or api-key or other security before doing anything

$cpuid = isset($_GET['cpuid']) ? $_GET['cpuid'] : '';
$name = isset($_GET['name']) ? $_GET['name'] : '';
$levelname = isset($_GET['levelname']) ? $_GET['levelname'] : '';
$message = isset($_GET['message']) ? $_GET['message'] : '';
$created = isset($_GET['created']) ? $_GET['created'] : '';

$dateTimeObj = new DateTime();
$dateTimeObj->setTimestamp(floatval($created));
$tcreated = $dateTimeObj->format('Y-m-d H:i:s');

require_once ('config.php');  //This is the config file with the database connection
require_once (TP_SOURCEPATH . 'CDBController.php'); // This is a database controller class
$rawlogmsg = json_encode($_GET);
$sql = "INSERT INTO Camlog (cpuid, raw, logtime, name, levelname, message, created ) VALUES "
    . "('{$cpuid}', '{$rawlogmsg}', Now(), '{$name}', '{$levelname}', '{$message}', '{$tcreated}')";
$db = new CDBController();
$mysqli = $db->Connect();
$res = $db->Query($sql);
$mysqli->close();
