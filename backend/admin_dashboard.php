<?php
/**
 * This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
 * The complete project is available at: https://github.com/teddycool/PyRpiCamController
 * The project is licensed under GNU GPLv3, check the LICENSE file for details.
 * 
 * @author teddycool
 */

require_once 'admin_auth.php';

// Require authentication to access this page
require_admin_auth();

// Add cache-busting headers to prevent browser caching issues
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

// Get current admin user info
start_admin_session();
$admin_username = $_SESSION['admin_username'] ?? 'admin';
$login_time = $_SESSION['admin_login_time'] ?? time();
?>
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>PyRpiCam OTA Management Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-content h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header-content p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .user-info {
            text-align: right;
        }
        
        .user-info .username {
            font-size: 1.1em;
            margin-bottom: 5px;
        }
        
        .user-info .login-time {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 10px;
        }
        
        .logout-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 8px 16px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9em;
            transition: background 0.3s ease;
        }
        
        .logout-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .tabs {
            display: flex;
            margin-bottom: 30px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .tab {
            flex: 1;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            border: none;
            background: white;
            color: #666;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        
        .tab.active {
            background: #667eea;
            color: white;
        }
        
        .tab:hover:not(.active) {
            background: #f0f0f0;
        }
        
        .content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-card h3 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .stat-card p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .table-container {
            overflow-x: auto;
            margin-top: 20px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin: 0 5px;
            transition: background 0.3s ease;
        }
        
        .btn:hover {
            background: #5a6fd8;
        }
        
        .btn-danger {
            background: #e74c3c;
        }
        
        .btn-danger:hover {
            background: #c0392b;
        }
        
        .btn-success {
            background: #27ae60;
        }
        
        .btn-success:hover {
            background: #229954;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background: white;
            margin: 15% auto;
            padding: 20px;
            border-radius: 10px;
            width: 90%;
            max-width: 500px;
        }
        
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .close:hover {
            color: black;
        }
        
        .status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .status.online {
            background: #d4edda;
            color: #155724;
        }
        
        .status.offline {
            background: #f8d7da;
            color: #721c24;
        }
        
        .status.pending {
            background: #fff3cd;
            color: #856404;
        }
        
        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        
        .success {
            background: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        
        .log-viewer {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .refresh-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 3px;
            padding: 5px 10px;
            cursor: pointer;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header {
                flex-direction: column;
                text-align: center;
                gap: 15px;
            }
            
            .header-content h1 {
                font-size: 2em;
            }
            
            .tabs {
                flex-direction: column;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .form-row {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-content">
                <h1>🎥 PyRpiCam OTA Dashboard</h1>
                <p>Uppdateringshantering för PyRpiCamController</p>
            </div>
            <div class="user-info">
                <div class="username">Inloggad: <?= htmlspecialchars($admin_username) ?></div>
                <div class="login-time">Sedan: <?= date('Y-m-d H:i:s', $login_time) ?></div>
                <a href="admin_logout.php" class="logout-btn">Logga ut</a>
            </div>
        </div>
        
        <!-- Cache notice for debugging -->
        <div id="cache-notice" style="background: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; margin-bottom: 20px; display: none;">
            <strong>💡 Tips:</strong> Om dashboard inte fungerar korrekt, prova att rensa webbläsarens cache:
            <br><strong>Firefox:</strong> Ctrl+Shift+R eller F5
            <br><strong>Chrome:</strong> Ctrl+Shift+R eller Ctrl+F5
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('devices')">Enheter</button>
            <button class="tab" onclick="showTab('versions')">Versioner</button>
            <button class="tab" onclick="showTab('logs')">Loggar</button>
            <button class="tab" onclick="showTab('settings')">Inställningar</button>
        </div>

        <!-- Devices Tab -->
        <div class="content">
            <div id="devices" class="tab-content active">
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3 id="total-devices">-</h3>
                        <p>Totalt antal enheter</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="online-devices">-</h3>
                        <p>Online enheter</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="pending-updates">-</h3>
                        <p>Väntande uppdateringar</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="last-update">-</h3>
                        <p>Senaste aktivitet</p>
                    </div>
                </div>
                
                <button class="btn" onclick="refreshDevices()">🔄 Uppdatera lista</button>
                
                <div class="table-container">
                    <table id="devices-table">
                        <thead>
                            <tr>
                                <th>Enhet ID</th>
                                <th>Modell</th>
                                <th>Aktuell version</th>
                                <th>Senaste kontakt</th>
                                <th>Status</th>
                                <th>Åtgärder</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="6" class="loading">Laddar enheter...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Versions Tab -->
            <div id="versions" class="tab-content">
                <h2>Versionshantering</h2>
                <p>Hantera tillgängliga programvaruversioner för uppdatering.</p>
                
                <button class="btn btn-success" onclick="showModal('uploadModal')">📦 Ladda upp ny version</button>
                <button class="btn" onclick="refreshVersions()">🔄 Uppdatera lista</button>
                
                <div class="table-container">
                    <table id="versions-table">
                        <thead>
                            <tr>
                                <th>Version</th>
                                <th>Datum</th>
                                <th>Filstorlek</th>
                                <th>Nedladdningar</th>
                                <th>Status</th>
                                <th>Åtgärder</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="6" class="loading">Laddar versioner...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Logs Tab -->
            <div id="logs" class="tab-content">
                <h2>Systemloggar</h2>
                <p>Visa systemloggar och uppdateringsaktivitet.</p>
                
                <div class="form-group">
                    <label for="log-type">Loggtyp:</label>
                    <select id="log-type" onchange="loadLogs()">
                        <option value="ota">OTA Uppdateringar</option>
                        <option value="system">Systemloggar</option>
                        <option value="errors">Felloggar</option>
                    </select>
                </div>
                
                <div style="position: relative;">
                    <button class="refresh-btn" onclick="loadLogs()">🔄</button>
                    <div id="log-content" class="log-viewer">Laddar loggar...</div>
                </div>
            </div>

            <!-- Settings Tab -->
            <div id="settings" class="tab-content">
                <h2>Systeminställningar</h2>
                <p>Konfigurera OTA-systemets inställningar.</p>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="update-server">Uppdateringsserver:</label>
                        <input type="url" id="update-server" placeholder="https://www.sensorwebben.se/pycamota/">
                    </div>
                    <div class="form-group">
                        <label for="update-group">Standardgrupp:</label>
                        <select id="update-group">
                            <option value="production">Production</option>
                            <option value="beta">Beta</option>
                            <option value="development">Development</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="maintenance-mode">Underhållsläge:</label>
                        <select id="maintenance-mode">
                            <option value="false">Inaktiverat</option>
                            <option value="true">Aktiverat</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="auto-cleanup">Auto-rensning (dagar):</label>
                        <input type="number" id="auto-cleanup" min="1" max="365" value="90">
                    </div>
                </div>
                
                <button class="btn btn-success" onclick="saveSettings()">💾 Spara inställningar</button>
            </div>
        </div>
    </div>

    <!-- Upload Modal -->
    <div id="uploadModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="hideModal('uploadModal')">&times;</span>
            <h2>Ladda upp ny version</h2>
            <form id="upload-form" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="version-number">Versionsnummer:</label>
                    <input type="text" id="version-number" required placeholder="t.ex. 3.1.0">
                </div>
                <div class="form-group">
                    <label for="version-file">Versionsfil (.tar.gz):</label>
                    <input type="file" id="version-file" accept=".tar.gz,.tgz" required>
                </div>
                <div class="form-group">
                    <label for="release-notes">Ändringskommentarer:</label>
                    <textarea id="release-notes" rows="4" placeholder="Beskriv vad som är nytt i denna version..."></textarea>
                </div>
                <button type="submit" class="btn btn-success">📦 Ladda upp</button>
            </form>
        </div>
    </div>

    <script>
        // API base URL - updated for subfolder deployment
        const API_BASE = '/pycamota';
        
        // Tab switching
        function showTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
            
            // Load data for the tab
            switch(tabName) {
                case 'devices':
                    loadDevices();
                    break;
                case 'versions':
                    loadVersions();
                    break;
                case 'logs':
                    loadLogs();
                    break;
                case 'settings':
                    loadSettings();
                    break;
            }
        }
        
        // Modal functions
        function showModal(modalId) {
            document.getElementById(modalId).style.display = 'block';
        }
        
        function hideModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        }
        
        // API helper function
        async function apiCall(endpoint, options = {}) {
            try {
                const response = await fetch(`${API_BASE}${endpoint}`, {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        ...options.headers
                    },
                    ...options
                });
                
                if (!response.ok) {
                    if (response.status === 401) {
                        // Session expired, redirect to login
                        window.location.href = 'admin_login.php';
                        return;
                    }
                    
                    // Try to get error message from response
                    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData.error) {
                            errorMessage = errorData.error;
                        }
                    } catch (e) {
                        // Response wasn't JSON
                    }
                    
                    throw new Error(errorMessage);
                }
                
                const data = await response.json();
                return data;
            } catch (error) {
                console.error('API call failed:', error);
                
                // Check if it's a network error
                if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    showError('Nätverksfel: Kan inte ansluta till servern');
                } else {
                    showError(`API-fel: ${error.message}`);
                }
                throw error;
            }
        }
        
        // Load devices
        async function loadDevices() {
            console.log('Loading devices...');
            try {
                // Use the working simple list API
                const response = await fetch(`${API_BASE}/api/simplelist`, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                console.log('Device data received:', data);
                
                if (!data.success) {
                    throw new Error(data.error || 'API call failed');
                }
                
                // Update stats using the statistics from the API
                const stats = data.statistics || {};
                document.getElementById('total-devices').textContent = stats.total_devices || 0;
                document.getElementById('online-devices').textContent = stats.active_devices || 0;
                document.getElementById('pending-updates').textContent = 0; // Will calculate if needed
                document.getElementById('last-update').textContent = 'Nu'; // Can improve this later
                
                // Update table
                const tbody = document.querySelector('#devices-table tbody');
                if (data.devices && data.devices.length > 0) {
                    tbody.innerHTML = data.devices.map(device => `
                        <tr>
                            <td>${escapeHtml(device.cpu_id || 'Okänt')}</td>
                            <td>${escapeHtml(device.device_name || 'Okänd')}</td>
                            <td>${escapeHtml(device.current_version || 'Okänd')}</td>
                            <td>${escapeHtml(device.last_seen || 'Aldrig')}</td>
                            <td><span class="status ${device.status || 'offline'}">${escapeHtml(device.status || 'offline')}</span></td>
                            <td>
                                <button class="btn" onclick="updateDevice('${escapeHtml(device.cpu_id || '')}')">🔄 Uppdatera</button>
                                <button class="btn btn-danger" onclick="deleteDevice('${escapeHtml(device.cpu_id || '')}')">🗑️ Ta bort</button>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="loading">Inga enheter registrerade.<br><br>Enheter registreras automatiskt när de ansluter för första gången.<br>Om du har enheter men de inte visas, kontrollera att de kör rätt programvara och kan nå servern.</td></tr>';
                }
            } catch (error) {
                console.error('Error loading devices:', error);
                const tbody = document.querySelector('#devices-table tbody');
                tbody.innerHTML = '<tr><td colspan="6" class="error">Fel vid laddning av enheter.<br><br>Detta kan bero på:<br>• Databasen är inte installerad<br>• Nätverksproblem<br>• Serverkonfigurationsfel<br><br>Kontrollera konsolen för mer information.</td></tr>';
                
                // Set default stats when there's an error
                document.getElementById('total-devices').textContent = '?';
                document.getElementById('online-devices').textContent = '?';
                document.getElementById('pending-updates').textContent = '?';
                document.getElementById('last-update').textContent = 'Fel';
            }
        }
        
        // Load versions
        async function loadVersions() {
            console.log('Loading versions...');
            try {
                const data = await apiCall('/version_management.php?action=list');
                console.log('Version data received:', data);
                
                const tbody = document.querySelector('#versions-table tbody');
                if (data.versions && data.versions.length > 0) {
                    tbody.innerHTML = data.versions.map(version => `
                        <tr>
                            <td>${escapeHtml(version.version || 'Okänd')}</td>
                            <td>${escapeHtml(version.release_date || version.date || 'Okänt')}</td>
                            <td>${escapeHtml(formatFileSize(version.file_size) || version.size || 'Okänt')}</td>
                            <td>${escapeHtml(version.device_count || version.downloads || '0')}</td>
                            <td><span class="status ${(version.status || 'unknown')}">${escapeHtml(version.status || 'okänt')}</span></td>
                            <td>
                                <button class="btn" onclick="downloadVersion('${escapeHtml(version.version || '')}')">📥 Ladda ner</button>
                                <button class="btn btn-danger" onclick="deleteVersion('${escapeHtml(version.version || '')}')">🗑️ Ta bort</button>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="loading">Inga versioner tillgängliga.<br><br>Ladda upp programvaruversioner genom att klicka på "Ladda upp ny version".<br>Versioner måste vara i .tar.gz format.</td></tr>';
                }
            } catch (error) {
                console.error('Error loading versions:', error);
                document.querySelector('#versions-table tbody').innerHTML = 
                    '<tr><td colspan="6" class="error">Fel vid laddning av versioner.<br><br>Detta kan bero på:<br>• Databasen är inte installerad<br>• Versionshanteringstabell saknas<br>• Serverkonfigurationsfel<br><br>Kontrollera konsolen för mer information.</td></tr>';
            }
        }
        
        // Load logs
        async function loadLogs() {
            const logType = document.getElementById('log-type').value;
            const logContent = document.getElementById('log-content');
            
            logContent.textContent = 'Laddar loggar...';
            
            try {
                const data = await apiCall(`/ota_report.php?action=logs&type=${logType}`);
                
                if (data.logs) {
                    logContent.textContent = data.logs;
                } else {
                    logContent.textContent = 'Inga loggar tillgängliga.';
                }
                
                // Auto-scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
            } catch (error) {
                logContent.textContent = 'Fel vid laddning av loggar.';
            }
        }
        
        // Load settings
        async function loadSettings() {
            try {
                const data = await apiCall('/config.php?action=get_settings');
                
                if (data.settings) {
                    document.getElementById('update-server').value = data.settings.update_server || '';
                    document.getElementById('update-group').value = data.settings.update_group || 'production';
                    document.getElementById('maintenance-mode').value = data.settings.maintenance_mode || 'false';
                    document.getElementById('auto-cleanup').value = data.settings.auto_cleanup || 90;
                }
            } catch (error) {
                showError('Fel vid laddning av inställningar.');
            }
        }
        
        // Save settings
        async function saveSettings() {
            try {
                const settings = {
                    update_server: document.getElementById('update-server').value,
                    update_group: document.getElementById('update-group').value,
                    maintenance_mode: document.getElementById('maintenance-mode').value,
                    auto_cleanup: document.getElementById('auto-cleanup').value
                };
                
                await apiCall('/config.php?action=save_settings', {
                    method: 'POST',
                    body: JSON.stringify(settings)
                });
                
                showSuccess('Inställningar sparade!');
            } catch (error) {
                showError('Fel vid sparande av inställningar.');
            }
        }
        
        // Refresh functions
        function refreshDevices() {
            loadDevices();
        }
        
        function refreshVersions() {
            loadVersions();
        }
        
        // Device actions
        async function updateDevice(deviceId) {
            if (confirm(`Är du säker på att du vill uppdatera enheten ${deviceId}?`)) {
                try {
                    await apiCall('/device_management.php?action=update', {
                        method: 'POST',
                        body: JSON.stringify({ device_id: deviceId })
                    });
                    
                    showSuccess(`Uppdatering initierad för enhet ${deviceId}`);
                    loadDevices();
                } catch (error) {
                    showError(`Fel vid uppdatering av enhet ${deviceId}`);
                }
            }
        }
        
        async function deleteDevice(deviceId) {
            if (confirm(`Är du säker på att du vill ta bort enheten ${deviceId}?`)) {
                try {
                    await apiCall('/device_management.php?action=delete', {
                        method: 'POST',
                        body: JSON.stringify({ device_id: deviceId })
                    });
                    
                    showSuccess(`Enhet ${deviceId} borttagen`);
                    loadDevices();
                } catch (error) {
                    showError(`Fel vid borttagning av enhet ${deviceId}`);
                }
            }
        }
        
        // Version actions
        async function deleteVersion(version) {
            if (confirm(`Är du säker på att du vill ta bort version ${version}?`)) {
                try {
                    await apiCall('/version_management.php?action=delete', {
                        method: 'POST',
                        body: JSON.stringify({ version: version })
                    });
                    
                    showSuccess(`Version ${version} borttagen`);
                    loadVersions();
                } catch (error) {
                    showError(`Fel vid borttagning av version ${version}`);
                }
            }
        }
        
        function downloadVersion(version) {
            window.open(`${API_BASE}/releases/${version}.tar.gz`, '_blank');
        }
        
        // File upload
        document.getElementById('upload-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('version', document.getElementById('version-number').value);
            formData.append('file', document.getElementById('version-file').files[0]);
            formData.append('notes', document.getElementById('release-notes').value);
            
            try {
                const response = await fetch(`${API_BASE}/version_management.php?action=upload`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    showSuccess('Version uppladdad!');
                    hideModal('uploadModal');
                    document.getElementById('upload-form').reset();
                    loadVersions();
                } else {
                    throw new Error(data.error || 'Okänt fel');
                }
            } catch (error) {
                showError(`Fel vid uppladdning: ${error.message}`);
            }
        });
        
        // Utility functions
        function escapeHtml(text) {
            if (typeof text !== 'string') return text;
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function formatFileSize(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            
            const container = document.querySelector('.container');
            container.insertBefore(errorDiv, container.firstChild);
            
            setTimeout(() => errorDiv.remove(), 5000);
        }
        
        function showSuccess(message) {
            const successDiv = document.createElement('div');
            successDiv.className = 'success';
            successDiv.textContent = message;
            
            const container = document.querySelector('.container');
            container.insertBefore(successDiv, container.firstChild);
            
            setTimeout(() => successDiv.remove(), 5000);
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Dashboard initializing...');
            console.log('API Base URL:', API_BASE);
            
            // Check if we can reach the API
            fetch(API_BASE + '/device_management.php?action=list')
                .then(response => {
                    console.log('Initial API test response:', response.status, response.statusText);
                    return response.text();
                })
                .then(text => {
                    console.log('Initial API test response body:', text.substring(0, 200) + '...');
                })
                .catch(error => {
                    console.error('Initial API test failed:', error);
                });
            
            // Load initial data
            loadDevices();
            
            // Show cache clearing instructions if there are issues
            setTimeout(() => {
                const errorElements = document.querySelectorAll('.error');
                if (errorElements.length > 0) {
                    console.warn('Errors detected - you may need to clear browser cache');
                    console.log('Firefox: Ctrl+Shift+R eller Ctrl+F5 för hård uppdatering');
                    console.log('Chrome: Ctrl+Shift+R eller Ctrl+F5');
                    
                    // Show cache notice
                    document.getElementById('cache-notice').style.display = 'block';
                }
            }, 2000);
        });
        
        // Auto-refresh every 30 seconds
        setInterval(function() {
            const activeTab = document.querySelector('.tab.active').textContent.toLowerCase();
            if (activeTab === 'enheter') {
                loadDevices();
            }
        }, 30000);
    </script>
</body>
</html>