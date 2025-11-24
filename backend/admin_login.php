<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

require_once 'admin_auth.php';

// If already authenticated, redirect to dashboard
if (is_admin_authenticated()) {
    header('Location: admin_dashboard.php');
    exit;
}

$error_message = '';

// Handle login form submission
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $client_ip = get_client_ip();
    
    // Check rate limiting
    if (!check_login_rate_limit($client_ip)) {
        $error_message = 'För många inloggningsförsök. Vänta 15 minuter.';
    } else {
        // Verify CSRF token
        if (!verify_csrf_token($_POST['csrf_token'] ?? '')) {
            $error_message = 'Säkerhetsfel. Försök igen.';
        } else {
            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';
            
            if (empty($username) || empty($password)) {
                $error_message = 'Användarnamn och lösenord krävs.';
            } else if (authenticate_admin($username, $password)) {
                // Successful login, redirect to dashboard
                header('Location: admin_dashboard.php');
                exit;
            } else {
                $error_message = 'Fel användarnamn eller lösenord.';
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyRpiCamController - Admin Inloggning</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .login-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            width: 100%;
            max-width: 400px;
            text-align: center;
        }

        .logo {
            width: 80px;
            height: 80px;
            background: #667eea;
            border-radius: 50%;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            color: white;
            font-weight: bold;
        }

        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 24px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }

        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }

        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }

        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 6px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn-login {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }

        .btn-login:disabled {
            opacity: 0.7;
            transform: none;
            cursor: not-allowed;
        }

        .error {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 12px;
        }

        @media (max-width: 480px) {
            .login-container {
                margin: 20px;
                padding: 30px 20px;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🎥</div>
        <h1>Admin Inloggning</h1>
        <p class="subtitle">PyRpiCamController OTA Management</p>
        
        <?php if (isset($error_message)): ?>
            <div class="error"><?= htmlspecialchars($error_message) ?></div>
        <?php endif; ?>
        
        <form method="POST" action="">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(generate_csrf_token()) ?>">
            
            <div class="form-group">
                <label for="username">Användarnamn:</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            
            <div class="form-group">
                <label for="password">Lösenord:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit" class="btn-login">Logga in</button>
        </form>
        
        <div class="footer">
            <p>PyRpiCamController v3.0</p>
            <p>&copy; 2025 Pär Sundbäck</p>
        </div>
    </div>

    <script>
        // Auto-focus on first empty field
        document.addEventListener('DOMContentLoaded', function() {
            const username = document.getElementById('username');
            const password = document.getElementById('password');
            
            if (!username.value) {
                username.focus();
            } else {
                password.focus();
            }
        });
        
        // Simple form validation
        document.querySelector('form').addEventListener('submit', function(e) {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                e.preventDefault();
                alert('Vänligen fyll i både användarnamn och lösenord.');
                return false;
            }
        });
    </script>
</body>
</html>