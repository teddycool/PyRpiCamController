<?php
/**
 * CamController OTA Admin Dashboard
 */
require_once __DIR__ . '/../utils/helpers.php';
require_admin_session();
$admin = current_admin();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CamController OTA — Admin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        body { background: #f8f9fa; }
        .navbar-brand { font-weight: 600; }
        .badge-draft      { background: #6c757d; }
        .badge-testing    { background: #0d6efd; }
        .badge-stable     { background: #198754; }
        .badge-deprecated { background: #dc3545; }
        .badge-stable_ch, .badge-testing_ch, .badge-beta { }
        th { white-space: nowrap; }
        .log-message { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        #toast-container { position: fixed; top: 1rem; right: 1rem; z-index: 9999; }
    </style>
</head>
<body>

<!-- Navbar -->
<nav class="navbar navbar-dark bg-dark px-3 mb-4">
    <span class="navbar-brand"><i class="bi bi-camera-video me-2"></i>CamController OTA</span>
    <div class="d-flex align-items-center gap-3">
        <span class="text-light small"><?= htmlspecialchars($admin['username']) ?></span>
        <a href="admin_logout.php" class="btn btn-sm btn-outline-light">Sign out</a>
    </div>
</nav>

<!-- Toast container -->
<div id="toast-container"></div>

<div class="container-fluid px-4">

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4" id="mainTabs">
        <li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#tab-releases">Releases</a></li>
        <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#tab-devices">Devices</a></li>
        <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#tab-logs">OTA Logs</a></li>
    </ul>

    <div class="tab-content">

        <!-- ================================================================ -->
        <!-- RELEASES TAB                                                      -->
        <!-- ================================================================ -->
        <div class="tab-pane fade show active" id="tab-releases">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="mb-0">Releases</h5>
                <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#uploadModal">
                    <i class="bi bi-upload me-1"></i>Upload release
                </button>
            </div>
            <div class="card shadow-sm">
                <div class="table-responsive">
                    <table class="table table-hover mb-0" id="releases-table">
                        <thead class="table-light">
                            <tr>
                                <th>Version</th>
                                <th>Channel</th>
                                <th>Status</th>
                                <th>Size</th>
                                <th>Checksum (SHA-256)</th>
                                <th>Uploaded</th>
                                <th>By</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="releases-body">
                            <tr><td colspan="8" class="text-center text-muted py-3">Loading…</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ================================================================ -->
        <!-- DEVICES TAB                                                        -->
        <!-- ================================================================ -->
        <div class="tab-pane fade" id="tab-devices">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="mb-0">Devices</h5>
                <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#addDeviceModal">
                    <i class="bi bi-plus-circle me-1"></i>Register device
                </button>
            </div>
            <div class="card shadow-sm">
                <div class="table-responsive">
                    <table class="table table-hover mb-0" id="devices-table">
                        <thead class="table-light">
                            <tr>
                                <th>Device ID</th>
                                <th>Name</th>
                                <th>Version</th>
                                <th>Channel</th>
                                <th>Active</th>
                                <th>Last seen</th>
                                <th>IP</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="devices-body">
                            <tr><td colspan="8" class="text-center text-muted py-3">Loading…</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ================================================================ -->
        <!-- LOGS TAB                                                           -->
        <!-- ================================================================ -->
        <div class="tab-pane fade" id="tab-logs">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="mb-0">OTA Logs</h5>
                <div class="d-flex gap-2">
                    <input type="text" id="log-filter-device" class="form-control form-control-sm" placeholder="Filter by device ID…" style="width:200px">
                    <button class="btn btn-outline-secondary btn-sm" onclick="loadLogs()"><i class="bi bi-arrow-clockwise"></i></button>
                </div>
            </div>
            <div class="card shadow-sm">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Time (UTC)</th>
                                <th>Device</th>
                                <th>Event</th>
                                <th>From</th>
                                <th>To</th>
                                <th>Result</th>
                                <th>IP</th>
                                <th>Message</th>
                            </tr>
                        </thead>
                        <tbody id="logs-body">
                            <tr><td colspan="8" class="text-center text-muted py-3">Loading…</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="card-footer d-flex gap-2 justify-content-end">
                    <button class="btn btn-sm btn-outline-secondary" id="logs-prev" onclick="logsPage(-1)" disabled>‹ Prev</button>
                    <span class="align-self-center small text-muted" id="logs-page-info"></span>
                    <button class="btn btn-sm btn-outline-secondary" id="logs-next" onclick="logsPage(1)">Next ›</button>
                </div>
            </div>
        </div>

    </div><!-- tab-content -->
</div><!-- container -->

<!-- ======================================================================== -->
<!-- MODALS                                                                     -->
<!-- ======================================================================== -->

<!-- Upload Release Modal -->
<div class="modal fade" id="uploadModal" tabindex="-1">
    <div class="modal-dialog">
        <form class="modal-content" id="upload-form" enctype="multipart/form-data">
            <div class="modal-header">
                <h5 class="modal-title">Upload Release</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="mb-3">
                    <label class="form-label">Package file (.tar.gz) <span class="text-danger">*</span></label>
                    <input type="file" name="file" class="form-control" accept=".tar.gz,.gz" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Version <span class="text-danger">*</span></label>
                    <input type="text" name="version" class="form-control" placeholder="1.0.3" required pattern="\d+\.\d+\.\d+.*">
                </div>
                <div class="mb-3">
                    <label class="form-label">Channel</label>
                    <select name="channel" class="form-select">
                        <option value="stable">stable</option>
                        <option value="testing">testing</option>
                        <option value="beta">beta</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Min required current version</label>
                    <input type="text" name="min_version" class="form-control" placeholder="optional — e.g. 1.0.0">
                </div>
                <div class="mb-3">
                    <label class="form-label">Release notes</label>
                    <textarea name="release_notes" class="form-control" rows="3"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary" id="upload-btn">
                    <span class="spinner-border spinner-border-sm d-none me-1" id="upload-spinner"></span>Upload
                </button>
            </div>
        </form>
    </div>
</div>

<!-- Add Device Modal -->
<div class="modal fade" id="addDeviceModal" tabindex="-1">
    <div class="modal-dialog">
        <form class="modal-content" id="add-device-form">
            <div class="modal-header">
                <h5 class="modal-title">Register Device</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="mb-3">
                    <label class="form-label">Device ID (CPU serial) <span class="text-danger">*</span></label>
                    <input type="text" name="device_id" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Name / Label</label>
                    <input type="text" name="name" class="form-control" placeholder="e.g. Kitchen cam">
                </div>
                <div class="mb-3">
                    <label class="form-label">Channel</label>
                    <select name="channel" class="form-select">
                        <option value="stable">stable</option>
                        <option value="testing">testing</option>
                        <option value="beta">beta</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Notes</label>
                    <textarea name="notes" class="form-control" rows="2"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Register</button>
            </div>
        </form>
    </div>
</div>

<!-- API Key result Modal -->
<div class="modal fade" id="apiKeyModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Device Registered</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="text-danger"><strong>Save this API key — it will not be shown again.</strong></p>
                <div class="input-group">
                    <input type="text" class="form-control font-monospace" id="new-api-key" readonly>
                    <button class="btn btn-outline-secondary" onclick="copyApiKey()">Copy</button>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Done</button>
            </div>
        </div>
    </div>
</div>

<!-- ======================================================================== -->
<!-- SCRIPTS                                                                    -->
<!-- ======================================================================== -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function toast(msg, type = 'success') {
    const el = document.createElement('div');
    el.className = `toast align-items-center text-bg-${type} border-0 show mb-2`;
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${msg}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => el.remove(), 4000);
}

async function api(method, url, body = null) {
    const opts = { method, credentials: 'same-origin' };
    if (body instanceof FormData) {
        opts.body = body;
    } else if (body) {
        opts.headers = { 'Content-Type': 'application/json' };
        opts.body = JSON.stringify(body);
    }
    const r = await fetch(url, opts);
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
}

function fmtSize(bytes) {
    if (!bytes) return '—';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
}
function fmtDate(s) { return s ? s.replace('T', ' ').substring(0, 16) : '—'; }

// ---------------------------------------------------------------------------
// Releases
// ---------------------------------------------------------------------------
async function loadReleases() {
    try {
        const rows = await api('GET', '../api/releases.php');
        const tbody = document.getElementById('releases-body');
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3">No releases yet.</td></tr>';
            return;
        }
        tbody.innerHTML = rows.map(r => `
            <tr>
                <td><strong>${r.version}</strong></td>
                <td><span class="badge bg-secondary">${r.channel}</span></td>
                <td><span class="badge badge-${r.status}"
                    style="background:${statusColor(r.status)}">${r.status}</span></td>
                <td>${fmtSize(r.filesize)}</td>
                <td class="font-monospace small" title="${r.checksum_sha256}">${r.checksum_sha256.substring(0,12)}…</td>
                <td class="small">${fmtDate(r.created_at)}</td>
                <td class="small">${r.uploaded_by_name || '—'}</td>
                <td>
                    <div class="d-flex gap-1">
                        <select class="form-select form-select-sm" style="width:110px"
                            onchange="promoteRelease(${r.id}, this.value)">
                            ${['draft','testing','stable','deprecated'].map(s =>
                                `<option value="${s}" ${s===r.status?'selected':''}>${s}</option>`
                            ).join('')}
                        </select>
                        <a href="../releases/${r.filename}" class="btn btn-sm btn-outline-secondary"
                            title="Download" target="_blank"><i class="bi bi-download"></i></a>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteRelease(${r.id}, '${r.version}')"
                            title="Delete"><i class="bi bi-trash"></i></button>
                    </div>
                </td>
            </tr>`).join('');
    } catch(e) { toast(e.message, 'danger'); }
}

function statusColor(s) {
    return {draft:'#6c757d', testing:'#0d6efd', stable:'#198754', deprecated:'#dc3545'}[s] || '#aaa';
}

async function promoteRelease(id, status) {
    try {
        await api('PATCH', `../api/releases.php?id=${id}`, { status });
        toast(`Release status → ${status}`);
        loadReleases();
    } catch(e) { toast(e.message, 'danger'); loadReleases(); }
}

async function deleteRelease(id, version) {
    if (!confirm(`Delete release ${version}? The file will be removed from disk.`)) return;
    try {
        await api('DELETE', `../api/releases.php?id=${id}`);
        toast(`Release ${version} deleted`);
        loadReleases();
    } catch(e) { toast(e.message, 'danger'); }
}

document.getElementById('upload-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('upload-btn');
    const spinner = document.getElementById('upload-spinner');
    btn.disabled = true; spinner.classList.remove('d-none');
    try {
        const fd = new FormData(e.target);
        const res = await api('POST', '../api/releases.php', fd);
        toast(`Release ${res.version} uploaded (${fmtSize(res.filesize)})`);
        bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
        e.target.reset();
        loadReleases();
    } catch(err) { toast(err.message, 'danger'); }
    finally { btn.disabled = false; spinner.classList.add('d-none'); }
});

// ---------------------------------------------------------------------------
// Devices
// ---------------------------------------------------------------------------
async function loadDevices() {
    try {
        const rows = await api('GET', '../api/devices.php');
        const tbody = document.getElementById('devices-body');
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3">No devices yet.</td></tr>';
            return;
        }
        tbody.innerHTML = rows.map(d => `
            <tr>
                <td class="font-monospace small">${d.device_id}</td>
                <td>${d.name || '<span class="text-muted">—</span>'}</td>
                <td>${d.current_version || '<span class="text-muted">—</span>'}</td>
                <td><span class="badge bg-secondary">${d.channel}</span></td>
                <td>${d.is_active
                    ? '<span class="badge bg-success">active</span>'
                    : '<span class="badge bg-secondary">inactive</span>'}</td>
                <td class="small">${fmtDate(d.last_seen)}</td>
                <td class="small">${d.last_ip || '—'}</td>
                <td>
                    <div class="d-flex gap-1">
                        <select class="form-select form-select-sm" style="width:100px"
                            onchange="changeDeviceChannel(${d.id}, this.value)">
                            ${['stable','testing','beta'].map(c =>
                                `<option value="${c}" ${c===d.channel?'selected':''}>${c}</option>`
                            ).join('')}
                        </select>
                        <button class="btn btn-sm btn-outline-secondary"
                            onclick="toggleDevice(${d.id}, ${d.is_active})"
                            title="${d.is_active ? 'Deactivate' : 'Activate'}">
                            <i class="bi bi-toggle-${d.is_active ? 'on' : 'off'}"></i></button>
                        <button class="btn btn-sm btn-outline-danger"
                            onclick="deleteDevice(${d.id}, '${d.device_id}')"
                            title="Delete"><i class="bi bi-trash"></i></button>
                    </div>
                </td>
            </tr>`).join('');
    } catch(e) { toast(e.message, 'danger'); }
}

async function changeDeviceChannel(id, channel) {
    try {
        await api('PUT', `../api/devices.php?id=${id}`, { channel });
        toast(`Channel updated to ${channel}`);
        loadDevices();
    } catch(e) { toast(e.message, 'danger'); loadDevices(); }
}

async function toggleDevice(id, current) {
    try {
        await api('PUT', `../api/devices.php?id=${id}`, { is_active: current ? 0 : 1 });
        toast(current ? 'Device deactivated' : 'Device activated');
        loadDevices();
    } catch(e) { toast(e.message, 'danger'); }
}

async function deleteDevice(id, device_id) {
    if (!confirm(`Delete device ${device_id}?`)) return;
    try {
        await api('DELETE', `../api/devices.php?id=${id}`);
        toast('Device deleted');
        loadDevices();
    } catch(e) { toast(e.message, 'danger'); }
}

document.getElementById('add-device-form').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    try {
        const res = await api('POST', '../api/devices.php', body);
        document.getElementById('new-api-key').value = res.api_key;
        bootstrap.Modal.getInstance(document.getElementById('addDeviceModal')).hide();
        e.target.reset();
        new bootstrap.Modal(document.getElementById('apiKeyModal')).show();
        loadDevices();
    } catch(err) { toast(err.message, 'danger'); }
});

function copyApiKey() {
    const el = document.getElementById('new-api-key');
    el.select(); document.execCommand('copy');
    toast('API key copied');
}

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------
let logsCurrentPage = 1;
const LOGS_PER_PAGE = 50;

async function loadLogs() {
    const deviceFilter = document.getElementById('log-filter-device').value.trim();
    const offset = (logsCurrentPage - 1) * LOGS_PER_PAGE;
    let url = `../api/logs.php?limit=${LOGS_PER_PAGE}&offset=${offset}`;
    if (deviceFilter) url += `&device_id=${encodeURIComponent(deviceFilter)}`;
    try {
        const res = await api('GET', url);
        const rows = res.rows || [];
        const total = res.total || 0;
        document.getElementById('logs-page-info').textContent =
            `${offset + 1}–${Math.min(offset + LOGS_PER_PAGE, total)} of ${total}`;
        document.getElementById('logs-prev').disabled = logsCurrentPage <= 1;
        document.getElementById('logs-next').disabled = offset + LOGS_PER_PAGE >= total;

        const tbody = document.getElementById('logs-body');
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3">No log entries.</td></tr>';
            return;
        }
        tbody.innerHTML = rows.map(l => `
            <tr>
                <td class="small">${l.created_at}</td>
                <td class="font-monospace small" title="${l.device_id}">${l.device_id.substring(0,12)}…</td>
                <td><span class="badge" style="background:${eventColor(l.event_type)}">${l.event_type}</span></td>
                <td class="small">${l.from_version || '—'}</td>
                <td class="small">${l.to_version   || '—'}</td>
                <td>${l.success === null ? '—'
                    : l.success == 1
                        ? '<span class="text-success">✓</span>'
                        : '<span class="text-danger">✗</span>'}</td>
                <td class="small">${l.client_ip || '—'}</td>
                <td class="small log-message" title="${(l.message||'').replace(/"/g,'&quot;')}">${l.message || '—'}</td>
            </tr>`).join('');
    } catch(e) { toast(e.message, 'danger'); }
}

function eventColor(t) {
    return {check:'#6c757d', download_start:'#0dcaf0', install_ok:'#198754',
            install_fail:'#dc3545', rollback:'#fd7e14'}[t] || '#aaa';
}

function logsPage(dir) {
    logsCurrentPage = Math.max(1, logsCurrentPage + dir);
    loadLogs();
}

document.getElementById('log-filter-device').addEventListener('input', () => {
    logsCurrentPage = 1; loadLogs();
});

// ---------------------------------------------------------------------------
// Tab activation — lazy load
// ---------------------------------------------------------------------------
document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
    tab.addEventListener('shown.bs.tab', e => {
        const target = e.target.getAttribute('href');
        if (target === '#tab-releases') loadReleases();
        if (target === '#tab-devices')  loadDevices();
        if (target === '#tab-logs')     loadLogs();
    });
});

// Initial load (releases tab is active)
loadReleases();
</script>
</body>
</html>
