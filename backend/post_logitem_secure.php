<?php
<?php
/*
 This file is a secure backend receiving script for log-items that are stored in a database table.
 It validates the API key before processing the log data.
*/

// Include required files for database connection
require_once('config.php');  // Config file with the database connection
require_once(TP_SOURCEPATH . 'CDBController.php'); // Database controller class

// Function to validate the API key
function validateApiKey($apiKey) {
    $db = new CDBController();
    $mysqli = $db->Connect();

    // Query to check if the API key exists in the cam-info table
    $stmt = $mysqli->prepare("SELECT COUNT(*) FROM `cam-info` WHERE `api_key` = ?");
    $stmt->bind_param("s", $apiKey);
    $stmt->execute();
    $stmt->bind_result($count);
    $stmt->fetch();
    $stmt->close();
    $mysqli->close();

    return $count > 0; // Return true if the API key is valid
}

// Get the API key from the Authorization header
$headers = getallheaders();
if (!isset($headers['Authorization'])) {
    http_response_code(401); // Unauthorized
    echo json_encode(["error" => "Missing Authorization header"]);
    exit;
}

$authHeader = $headers['Authorization'];
if (!preg_match('/Bearer\s(\S+)/', $authHeader, $matches)) {
    http_response_code(401); // Unauthorized
    echo json_encode(["error" => "Invalid Authorization header format"]);
    exit;
}

$apiKey = $matches[1];

// Validate the API key
if (!validateApiKey($apiKey)) {
    http_response_code(403); // Forbidden
    echo json_encode(["error" => "Invalid API key"]);
    exit;
}

// Read the JSON payload from the POST request body
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    http_response_code(400); // Bad Request
    echo json_encode(["error" => "Invalid JSON payload"]);
    exit;
}

// Extract log data from the JSON payload
$cpuid = isset($data['cpuid']) ? $data['cpuid'] : '';
$name = isset($data['logname']) ? $data['logname'] : '';
$levelname = isset($data['logLevel']) ? $data['logLevel'] : '';
$message = isset($data['message']) ? $data['message'] : '';
$created = isset($data['time']) ? $data['time'] : '';

$dateTimeObj = new DateTime();
$dateTimeObj->setTimestamp(strtotime($created));
$tcreated = $dateTimeObj->format('Y-m-d H:i:s');

// Insert the log data into the database
$rawlogmsg = json_encode($data);
$sql = "INSERT INTO Camlog (cpuid, raw, logtime, name, levelname, message, created) VALUES "
    . "(?, ?, Now(), ?, ?, ?, ?)";

$db = new CDBController();
$mysqli = $db->Connect();
$stmt = $mysqli->prepare($sql);
$stmt->bind_param("ssssss", $cpuid, $rawlogmsg, $name, $levelname, $message, $tcreated);
$stmt->execute();
$stmt->close();
$mysqli->close();

// Respond with success
http_response_code(200); // OK
echo json_encode(["success" => true]);