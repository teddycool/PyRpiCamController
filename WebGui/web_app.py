# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from flask import Flask, render_template, request, redirect, jsonify, flash
import sys
import os
import json as json_module  # Use different name to avoid conflicts
import socket
import time
import datetime
import shutil
# Add parent directory to path to access Settings module
from Settings.settings_manager import settings_manager

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key

@app.route("/", methods=["GET"])
def index():
    """Main settings form with basic/advanced tabs."""
    level = request.args.get('level', 'basic')  # Default to basic settings
    
    # Display form
    ui_schema = settings_manager.get_web_editable_schema()
    
    # Filter by level and group by section
    filtered_schema = {}
    current_values = {}
    
    for field, schema_info in ui_schema.items():
        setting_level = schema_info.get('level', 'basic')  # Default to basic if not specified
        
        # Only show settings for the current level
        if setting_level != level:
            continue
            
        section = schema_info['section']
        if section not in filtered_schema:
            filtered_schema[section] = []
        
        filtered_schema[section].append((field, schema_info))
        current_values[field] = settings_manager.get(field)
    
    return render_template(
        "settings_form.html",
        grouped_schema=filtered_schema,
        current_values=current_values,
        current_level=level
    )

def convert_form_value(raw_value, schema_info):
    """Convert form string value to appropriate Python type."""
    setting_type = schema_info['type']
    
    if setting_type == 'int':
        value = int(raw_value)
    elif setting_type == 'float':
        value = float(raw_value)
    elif setting_type == 'bool':
        # Handle both string values (from forms) and boolean values (from AJAX)
        if isinstance(raw_value, bool):
            value = raw_value
        elif isinstance(raw_value, str):
            value = raw_value.lower() in ('true', '1', 'on', 'yes')
        else:
            # Convert other types to boolean
            value = bool(raw_value)
    elif setting_type == 'tuple':
        # Handle tuple input - expect comma-separated values
        try:
            # Try to parse as JSON first
            import json
            value = json.loads(raw_value)
            if not isinstance(value, (list, tuple)):
                raise ValueError("Expected list/tuple")
        except:
            # Fall back to comma-separated parsing
            parts = [part.strip() for part in raw_value.split(',')]
            # Try to convert to numbers if possible
            converted_parts = []
            for part in parts:
                try:
                    if '.' in part:
                        converted_parts.append(float(part))
                    else:
                        converted_parts.append(int(part))
                except ValueError:
                    converted_parts.append(part)
            value = converted_parts
    elif setting_type == 'enum':
        # Handle JSON string values for array enums (like resolution)
        if isinstance(raw_value, str) and raw_value.startswith('['):
            try:
                value = json_module.loads(raw_value)
            except json_module.JSONDecodeError:
                value = raw_value
        else:
            value = raw_value
        # Validation happens in settings_manager
    elif setting_type == 'text' or setting_type == 'password':
        value = str(raw_value)
    else:
        value = raw_value
    
    return value


@app.route("/api/stream/status")
def stream_status():
    """Get current streaming status"""
    try:
        # Check if streaming server is running
        port = settings_manager.get('Stream.port')
        hostname = socket.gethostname()
        
        # Try to connect to streaming server to check if it's running
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            is_running = (result == 0)
        except:
            is_running = False
        
        # Get stream runtime details if streaming is running
        actual_fps = 0.0
        stream_clients = 0
        stream_capture_mode = 'stopped'
        stream_idling = False
        if is_running:
            try:
                import requests
                response = requests.get(f'http://localhost:{port}/api/info', timeout=2)
                if response.status_code == 200:
                    stream_info = response.json()
                    actual_fps = stream_info.get('actual_fps', 0.0)
                    stream_clients = int(stream_info.get('clients', 0) or 0)
                    stream_idling = stream_clients == 0
                    stream_capture_mode = 'idle' if stream_idling else 'active'
            except:
                # Fallback if streaming server API is not available
                actual_fps = 0.0
                stream_clients = 0
                stream_capture_mode = 'active'
                stream_idling = False
        
        # Read current temperature data from runtime status file
        temperature_data = {
            'cpu_temperature': None,
            'ds18b20_temperature': None,
            'ds18b20_available': False,
            'temperature_timestamp': None
        }
        
        try:
            runtime_status_file = "/tmp/cam_runtime_status.json"
            if os.path.exists(runtime_status_file):
                # Try multiple times in case file is being written
                for attempt in range(3):
                    try:
                        with open(runtime_status_file, 'r') as f:
                            status_data = json_module.load(f)
                            temperature_data['cpu_temperature'] = status_data.get('cpu_temperature')
                            temperature_data['ds18b20_temperature'] = status_data.get('ds18b20_temperature')
                            temperature_data['ds18b20_available'] = status_data.get('ds18b20_available', False)
                            temperature_data['temperature_timestamp'] = status_data.get('timestamp')
                        break  # Success, exit retry loop
                    except (json_module.JSONDecodeError, IOError) as e:
                        if attempt < 2:  # Retry on first two attempts
                            time.sleep(0.1)
                            continue
                        else:
                            # Give up after 3 attempts
                            pass
        except Exception as e:
            # Temperature data not available, keep None values
            pass

        # Read disk usage for image storage location
        disk_data = {
            'disk_total_bytes': None,
            'disk_free_bytes': None,
            'disk_path': None
        }

        cpu_load_data = {
            'cpu_load_percent': None,
            'cpu_load_1min': None,
            'cpu_cores': None,
        }

        try:
            disk_path = settings_manager.get('Cam.publishers.file.location')
            if not disk_path:
                disk_path = '/'

            # Use directory itself when possible; otherwise inspect parent directory
            usage_path = disk_path if os.path.isdir(disk_path) else os.path.dirname(disk_path) or '/'
            usage = shutil.disk_usage(usage_path)

            disk_data['disk_total_bytes'] = usage.total
            disk_data['disk_free_bytes'] = usage.free
            disk_data['disk_path'] = usage_path
        except Exception:
            # Disk data not available, keep None values
            pass

        try:
            cpu_count = os.cpu_count() or 1
            load_1min, _, _ = os.getloadavg()
            cpu_load_percent = (load_1min / cpu_count) * 100.0

            cpu_load_data['cpu_load_percent'] = round(cpu_load_percent, 1)
            cpu_load_data['cpu_load_1min'] = round(load_1min, 2)
            cpu_load_data['cpu_cores'] = cpu_count
        except Exception:
            # CPU load data not available, keep None values
            pass
        
        response_data = {
            'running': is_running,
            'port': port,
            'url': f"http://{hostname}.local:{port}",
            'resolution': settings_manager.get('Stream.resolution'),
            'framerate': settings_manager.get('Stream.framerate'),
            'actual_fps': actual_fps,
            'stream_clients': stream_clients,
            'stream_capture_mode': stream_capture_mode,
            'stream_idling': stream_idling,
        }
        
        # Add temperature data to response
        response_data.update(temperature_data)
        response_data.update(disk_data)
        response_data.update(cpu_load_data)
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Streaming control removed - now handled by Mode setting

@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update settings via AJAX - supports both single and bulk updates"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        print(f"Settings update request: {data}")
        
        # Get editable schema for validation
        ui_schema = settings_manager.get_web_editable_schema()
        updated_fields = []
        
        # Handle both formats: {field: value} or {field: field_name, value: field_value}
        if 'field' in data and 'value' in data:
            # Format: {field: "Mode", value: "Photo"}
            field = data.get('field')
            value = data.get('value')
            fields_to_update = {field: value}
        else:
            # Format: {Mode: "Photo", LogLevel: "DEBUG", ...}
            fields_to_update = data
        
        for field, value in fields_to_update.items():
            
            if field not in ui_schema:
                print(f"Warning: Field {field} not found or not editable, skipping")
                continue

            schema_info = ui_schema[field]
            
            # Convert value based on type
            converted_value = convert_form_value(value, schema_info)
            # Save the setting
            settings_manager.set(field, converted_value, save=True)
            
            # Track this change for restart notification
            track_setting_change(field, converted_value)
            
            updated_fields.append({
                'field': field,
                'value': converted_value
            })
        
        return jsonify({
            'success': True, 
            'message': f'Updated {len(updated_fields)} setting(s)',
            'updated_fields': updated_fields,
            'pending_changes': get_pending_changes()
        })
        
    except Exception as e:
        error_msg = f"Error updating settings: {str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500


@app.route("/api/settings/update", methods=["POST"])
def update_setting():
    """Update a single setting via AJAX"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        field = data.get('field')
        value = data.get('value')
        
        print(f"Settings update request - Field: {field}, Value: {value}, Type: {type(value)}")
        
        if not field:
            return jsonify({'error': 'Field name required'}), 400
        
        # Get schema info for validation
        ui_schema = settings_manager.get_web_editable_schema()
        if field not in ui_schema:
            return jsonify({'error': f'Field {field} not found or not editable'}), 400
        
        schema_info = ui_schema[field]
        
        # Convert value based on type
        converted_value = convert_form_value(value, schema_info)
        
        # Save the setting
        settings_manager.set(field, converted_value, save=True)
        
        # Track this change for restart notification
        track_setting_change(field, converted_value)
        
        print(f"Settings saved successfully - {field}: {converted_value}")
        
        return jsonify({
            'success': True, 
            'message': f'Setting {field} updated',
            'field': field,
            'value': converted_value,
            'pending_changes': get_pending_changes()
        })
    except Exception as e:
        error_msg = f"Error updating setting {field if 'field' in locals() else 'unknown'}: {str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500


# Persistent pending changes tracking
PENDING_CHANGES_FILE = "/tmp/webgui_pending_changes.json"

def load_pending_changes():
    """Load pending changes from file"""
    try:
        if os.path.exists(PENDING_CHANGES_FILE):
            with open(PENDING_CHANGES_FILE, 'r') as f:
                return json_module.load(f)
    except:
        pass
    return {}

def save_pending_changes_to_file(changes):
    """Save pending changes to file"""
    try:
        with open(PENDING_CHANGES_FILE, 'w') as f:
            json_module.dump(changes, f)
    except Exception as e:
        print(f"Error saving pending changes: {e}")

def track_setting_change(field, value):
    """Track a setting change for restart notification"""
    pending_changes = load_pending_changes()
    pending_changes[field] = {
        'value': value,
        'timestamp': time.time()
    }
    save_pending_changes_to_file(pending_changes)

def get_pending_changes():
    """Get list of pending changes"""
    pending_changes = load_pending_changes()
    return {
        'count': len(pending_changes),
        'changes': {k: v['value'] for k, v in pending_changes.items()}
    }

def clear_pending_changes():
    """Clear pending changes after restart"""
    try:
        if os.path.exists(PENDING_CHANGES_FILE):
            os.remove(PENDING_CHANGES_FILE)
    except Exception as e:
        print(f"Error clearing pending changes: {e}")


@app.route("/api/settings/pending")
def get_pending_settings():
    """Get current pending changes"""
    return jsonify(get_pending_changes())


@app.route("/api/service/apply-and-restart", methods=["POST"])
def apply_and_restart():
    """Apply all changes and restart the camera service"""
    try:
        changes = get_pending_changes()
        
        if changes['count'] == 0:
            return jsonify({
                'success': True,
                'message': 'No pending changes to apply',
                'action': 'none'
            })
        
        # Refresh in-memory view from disk before requesting service restart.
        # Pending changes are informational only and must not overwrite persisted settings.
        settings_manager.load_user_settings()

        # All setting changes are restart-only by policy.
        restart_file = "/tmp/cam_reload_settings.txt"
        with open(restart_file, 'w') as f:
            f.write("restart_service\n")

        restart_message = f'Applied {changes["count"]} changes and requested full service restart'
        
        # Clear pending changes after successful persistence + reload request write.
        clear_pending_changes()
        
        return jsonify({
            'success': True,
            'message': restart_message,
            'action': 'restart',
            'changes_applied': changes['changes']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/settings/debug", methods=["GET"])
def settings_debug():
    """Debug endpoint to check current settings state"""
    try:
        debug_info = {
            'current_mode': settings_manager.get('Mode'),
            'status': 'OK'
        }
        
        try:
            # Try to get more detailed info
            settings_dict = dict(settings_manager.get_dict())
            debug_info.update({
                'all_settings_count': len(settings_dict),
                'mode_related': {k: v for k, v in settings_dict.items() if 'mode' in k.lower()}
            })
        except Exception as e:
            debug_info['settings_dict_error'] = str(e)
        
        try:
            # Try to get file info
            import os
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_file = os.path.join(script_dir, "Settings", "user_settings.json")
            
            debug_info.update({
                'user_settings_file': user_file,
                'user_file_exists': os.path.exists(user_file)
            })
            
            if os.path.exists(user_file):
                debug_info['user_file_writable'] = os.access(user_file, os.W_OK)
                with open(user_file, 'r') as f:
                    content = f.read()
                    debug_info['user_file_size'] = len(content)
                    # Only include first part to avoid large responses
                    if len(content) > 300:
                        debug_info['user_file_content'] = content[:300] + "..."
                    else:
                        debug_info['user_file_content'] = content
            
        except Exception as e:
            debug_info['file_info_error'] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'ERROR'
        }), 500


@app.route("/api/test")
def test_endpoint():
    """Simple test endpoint to verify Flask is working"""
    return jsonify({
        'status': 'OK',
        'message': 'Flask server is responding',
        'current_mode': settings_manager.get('Mode')
    })


# Update Management Endpoints
@app.route("/api/updates/status")
def get_update_status():
    """Get current update status information"""
    try:
        # Get version info from VERSION file
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'VERSION')
        current_version = "Unknown"
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                current_version = f.read().strip()
        
        update_info = {
            'current_version': current_version,
            'available_version': settings_manager.get('OTA.available_version', ''),
            'last_check': settings_manager.get('OTA.last_check', 'Never'),
            'update_status': settings_manager.get('OTA.update_status', 'idle'),
            'auto_apply': settings_manager.get('OTA.auto_apply'),
            'notify_available': settings_manager.get('OTA.notify_available', True),
            'has_update': False,
            'changelog': ''
        }
        
        # Check if update is available
        if (update_info['available_version'] and 
            update_info['available_version'] != current_version and
            update_info['available_version'] != ''):
            update_info['has_update'] = True
            
        return jsonify(update_info)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get update status: {str(e)}'}), 500


@app.route("/api/updates/check", methods=["POST"])
def check_for_updates():
    """Manually trigger update check"""
    try:
        # Update status to checking
        settings_manager.set('OTA.update_status', 'checking', save=True)
        settings_manager.set('OTA.last_check', time.strftime('%Y-%m-%d %H:%M:%S'), save=True)
        
        # Create update check trigger file (to be picked up by OTA daemon)
        check_file_path = "/tmp/ota_check_trigger"
        with open(check_file_path, 'w') as f:
            f.write(f"manual check requested at {time.time()}")
        
        return jsonify({
            'success': True,
            'message': 'Update check initiated',
            'status': 'checking'
        })
        
    except Exception as e:
        settings_manager.set('OTA.update_status', 'error', save=True)
        return jsonify({'error': f'Failed to start update check: {str(e)}'}), 500


@app.route("/api/updates/apply", methods=["POST"])
def apply_update():
    """User-triggered update application with backup"""
    try:
        # Check if update is available
        current_version = settings_manager.get('OTA.current_version', '')
        available_version = settings_manager.get('OTA.available_version', '')
        
        if not available_version or available_version == current_version:
            return jsonify({'error': 'No update available to apply'}), 400
        
        # Update status to applying
        settings_manager.set('OTA.update_status', 'applying', save=True)
        
        # Create backup before update
        backup_info = create_backup()
        
        # Create update apply trigger file
        apply_file_path = "/tmp/ota_apply_trigger"
        with open(apply_file_path, 'w') as f:
            f.write(f"manual update apply requested at {time.time()}\n")
            f.write(f"backup_id: {backup_info['backup_id']}\n")
            f.write(f"from_version: {current_version}\n")
            f.write(f"to_version: {available_version}\n")
        
        return jsonify({
            'success': True,
            'message': f'Update application initiated (v{current_version} → v{available_version})',
            'backup_id': backup_info['backup_id'],
            'status': 'applying'
        })
        
    except Exception as e:
        settings_manager.set('OTA.update_status', 'error', save=True)
        return jsonify({'error': f'Failed to apply update: {str(e)}'}), 500


@app.route("/api/updates/changelog")
def get_changelog():
    """Get changelog for available update"""
    try:
        # Try to read changelog from download directory
        changelog_file = "/tmp/ota_changelog.txt"
        changelog = "No changelog available"
        
        if os.path.exists(changelog_file):
            with open(changelog_file, 'r') as f:
                changelog = f.read()
        
        return jsonify({
            'changelog': changelog,
            'available_version': settings_manager.get('OTA.available_version', ''),
            'current_version': settings_manager.get('OTA.current_version', '')
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get changelog: {str(e)}'}), 500


@app.route("/api/updates/backup", methods=["POST"])
def create_backup():
    """Create backup of current installation"""
    try:
        backup_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        install_path = settings_manager.get('OTA.install_path', '/home/pi/PyRpiCamController')
        backup_dir = f"/tmp/backups/backup_{backup_id}"
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup info file
        backup_info_file = os.path.join(backup_dir, 'backup_info.json')
        backup_info = {
            'backup_id': backup_id,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': settings_manager.get('OTA.current_version', ''),
            'install_path': install_path,
            'settings_backup': True,
            'code_backup': False  # We'll implement this if needed
        }
        
        # Backup settings
        settings_backup_dir = os.path.join(backup_dir, 'settings')
        os.makedirs(settings_backup_dir, exist_ok=True)
        
        # Copy settings files
        import shutil
        settings_dir = os.path.join(install_path, 'Settings')
        if os.path.exists(settings_dir):
            shutil.copytree(settings_dir, os.path.join(settings_backup_dir, 'Settings'))
        
        # Save backup info
        with open(backup_info_file, 'w') as f:
            json_module.dump(backup_info, f, indent=2)
        
        return backup_info
        
    except Exception as e:
        raise Exception(f'Backup creation failed: {str(e)}')


# Old separate reload/restart endpoints replaced by unified apply-and-restart
# @app.route("/api/settings/reload", methods=["POST"])
# @app.route("/api/service/restart", methods=["POST"])


@app.route("/stream")
def stream_redirect():
    """Redirect to streaming server"""
    port = settings_manager.get('Stream.port')
    hostname = socket.gethostname()
    return redirect(f"http://{hostname}.local:{port}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)