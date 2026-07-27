<?php
/**
 * Admin API — release management.
 *
 * Routes (all require active admin session):
 *   GET    /api/releases.php             — list all releases
 *   POST   /api/releases.php             — upload a new release (multipart/form-data)
 *   PATCH  /api/releases.php?id=<n>      — update status / release_notes / channel
 *   DELETE /api/releases.php?id=<n>      — delete release (+ file on disk)
 *
 * Upload form fields:
 *   file           (file)   required — .tar.gz package
 *   version        (string) required — e.g. "1.0.3"
 *   channel        (string) optional — stable | testing | beta  (default: stable)
 *   release_notes  (string) optional
 *   min_version    (string) optional — minimum current version that may receive this
 */

require_once __DIR__ . '/../utils/helpers.php';

require_admin_api();

$method = $_SERVER['REQUEST_METHOD'];
// Allow POST with _method override for hosts that block PATCH/PUT/DELETE
if ($method === 'POST') {
    $peek = json_decode(file_get_contents('php://input'), true);
    if (!empty($peek['_method'])) {
        $method = strtoupper($peek['_method']);
    }
    // Stash decoded body so json_body() doesn't need to re-read php://input
    if ($peek !== null) {
        $GLOBALS['_json_body_cache'] = $peek;
    }
}
$id = isset($_GET['id']) ? (int) $_GET['id'] : null;
$pdo    = cam_db();

// Ensure releases directory exists
if (!is_dir(CAM_RELEASES_DIR)) {
    mkdir(CAM_RELEASES_DIR, 0755, true);
}

// ---------------------------------------------------------------------------
// GET — list releases
// ---------------------------------------------------------------------------
if ($method === 'GET') {
    $rows = $pdo->query("
        SELECT r.*, a.username AS uploaded_by_name
        FROM   cam_releases r
        LEFT   JOIN cam_admins a ON a.id = r.uploaded_by
        ORDER  BY r.created_at DESC
    ")->fetchAll();

    json_ok($rows);
}

// ---------------------------------------------------------------------------
// POST — upload new release
// ---------------------------------------------------------------------------
if ($method === 'POST') {
    if (empty($_FILES['file'])) {
        json_error('No file uploaded');
    }

    $version      = trim($_POST['version']       ?? '');
    $channel      = trim($_POST['channel']        ?? 'stable');
    $release_notes = trim($_POST['release_notes'] ?? '');
    $min_version  = trim($_POST['min_version']    ?? '');

    if (!$version) {
        json_error('version is required');
    }
    if (!preg_match('/^\d+\.\d+\.\d+/', $version)) {
        json_error('version must be semver (e.g. 1.0.3)');
    }
    if (!in_array($channel, ['stable', 'testing', 'beta'], true)) {
        json_error('channel must be stable, testing, or beta');
    }

    $upload = $_FILES['file'];

    if ($upload['error'] !== UPLOAD_ERR_OK) {
        json_error('Upload error code: ' . $upload['error']);
    }
    if ($upload['size'] > CAM_MAX_UPLOAD_BYTES) {
        json_error('File exceeds max size (' . (CAM_MAX_UPLOAD_BYTES / 1024 / 1024) . ' MB)');
    }

    // Validate MIME / magic bytes for .tar.gz
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime  = finfo_file($finfo, $upload['tmp_name']);
    finfo_close($finfo);

    $allowed_mimes = ['application/gzip', 'application/x-gzip', 'application/x-tar',
                      'application/octet-stream'];
    if (!in_array($mime, $allowed_mimes, true)) {
        json_error('File must be a .tar.gz archive (detected: ' . $mime . ')');
    }

    // Sanitize filename: PyRpiCamController-{version}.tar.gz
    $filename = 'PyRpiCamController-' . preg_replace('/[^a-zA-Z0-9._-]/', '', $version) . '.tar.gz';
    $dest     = CAM_RELEASES_DIR . '/' . $filename;

    if (!move_uploaded_file($upload['tmp_name'], $dest)) {
        json_error('Failed to store uploaded file', 500);
    }

    $checksum = sha256_file($dest);
    $filesize = filesize($dest);

    // Retrieve current admin id from session
    session_name(CAM_SESSION_NAME);
    if (session_status() === PHP_SESSION_NONE) session_start();
    $admin_id = $_SESSION['admin_id'] ?? null;

    try {
        $stmt = $pdo->prepare("
            INSERT INTO cam_releases
                (version, channel, status, filename, filesize, checksum_sha256,
                 min_version, release_notes, uploaded_by)
            VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute([
            $version,
            $channel,
            $filename,
            $filesize,
            $checksum,
            $min_version ?: null,
            $release_notes ?: null,
            $admin_id,
        ]);
        $new_id = (int) $pdo->lastInsertId();
    } catch (PDOException $e) {
        @unlink($dest);
        if ($e->getCode() === '23000') {
            json_error("Release $version/$channel already exists", 409);
        }
        json_error('Database error', 500);
    }

    json_ok([
        'id'              => $new_id,
        'version'         => $version,
        'channel'         => $channel,
        'status'          => 'draft',
        'filename'        => $filename,
        'filesize'        => $filesize,
        'checksum_sha256' => $checksum,
        'download_url'    => CAM_RELEASES_URL . '/' . $filename,
    ], 201);
}

// ---------------------------------------------------------------------------
// PATCH — update status / notes
// ---------------------------------------------------------------------------
if ($method === 'PATCH') {
    if (!$id) {
        json_error('id is required');
    }

    $body   = json_body();
    $fields = [];
    $params = [];

    $allowed_statuses = ['draft', 'testing', 'stable', 'deprecated'];

    if (array_key_exists('status', $body)) {
        if (!in_array($body['status'], $allowed_statuses, true)) {
            json_error('Invalid status. Allowed: ' . implode(', ', $allowed_statuses));
        }
        $fields[] = 'status = ?';
        $params[] = $body['status'];
    }
    if (array_key_exists('release_notes', $body)) {
        $fields[] = 'release_notes = ?';
        $params[] = $body['release_notes'];
    }
    if (array_key_exists('channel', $body)) {
        $fields[] = 'channel = ?';
        $params[] = $body['channel'];
    }
    if (array_key_exists('min_version', $body)) {
        $fields[] = 'min_version = ?';
        $params[] = $body['min_version'] ?: null;
    }

    if (!$fields) {
        json_error('No updatable fields (status, release_notes, channel, min_version)');
    }

    $params[] = $id;
    $pdo->prepare('UPDATE cam_releases SET ' . implode(', ', $fields) . ' WHERE id = ?')
        ->execute($params);

    json_ok(['updated' => true]);
}

// ---------------------------------------------------------------------------
// DELETE — remove release
// ---------------------------------------------------------------------------
if ($method === 'DELETE') {
    if (!$id) {
        json_error('id is required');
    }

    $stmt = $pdo->prepare('SELECT filename FROM cam_releases WHERE id = ?');
    $stmt->execute([$id]);
    $row = $stmt->fetch();

    if (!$row) {
        json_error('Release not found', 404);
    }

    // Remove file from disk
    $filepath = CAM_RELEASES_DIR . '/' . $row['filename'];
    if (file_exists($filepath)) {
        @unlink($filepath);
    }

    $pdo->prepare('DELETE FROM cam_releases WHERE id = ?')->execute([$id]);
    json_ok(['deleted' => true]);
}

json_error('Method not allowed', 405);
