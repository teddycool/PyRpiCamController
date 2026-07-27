<?php
/**
 * Admin login page.
 */
require_once __DIR__ . '/../utils/config.php';

session_name(CAM_SESSION_NAME);
session_start();

// Already logged in
if (!empty($_SESSION['admin_id'])) {
    header('Location: admin_dashboard.php');
    exit;
}

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if ($username && $password) {
        try {
            $stmt = cam_db()->prepare(
                'SELECT id, password_hash FROM cam_admins WHERE username = ? AND is_active = 1'
            );
            $stmt->execute([$username]);
            $admin = $stmt->fetch();

            if ($admin && password_verify($password, $admin['password_hash'])) {
                session_regenerate_id(true);
                $_SESSION['admin_id']       = $admin['id'];
                $_SESSION['admin_username'] = $username;

                // Update last_login
                cam_db()->prepare('UPDATE cam_admins SET last_login = NOW() WHERE id = ?')
                        ->execute([$admin['id']]);

                header('Location: admin_dashboard.php');
                exit;
            } else {
                $error = 'Invalid username or password.';
            }
        } catch (Exception $e) {
            $error = 'Database error. Please try again.';
        }
    } else {
        $error = 'Please enter username and password.';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CamController OTA — Admin Login</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
    <style>
        body { background: #f0f2f5; }
        .login-card { max-width: 380px; margin: 100px auto; }
    </style>
</head>
<body>
<div class="login-card card shadow-sm">
    <div class="card-body p-4">
        <h4 class="card-title mb-4 text-center">CamController OTA</h4>
        <?php if ($error): ?>
            <div class="alert alert-danger py-2"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>
        <form method="post" autocomplete="off">
            <div class="mb-3">
                <label class="form-label">Username</label>
                <input type="text" name="username" class="form-control" autofocus required
                       value="<?= htmlspecialchars($_POST['username'] ?? '') ?>">
            </div>
            <div class="mb-3">
                <label class="form-label">Password</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-primary w-100">Sign in</button>
        </form>
    </div>
</div>
</body>
</html>
