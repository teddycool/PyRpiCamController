# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from flask import Flask, render_template, request, redirect, jsonify, flash
import sys
import os
import json
import socket
# Add parent directory to path to access Settings module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Settings.settings_manager import settings_manager

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key

@app.route("/", methods=["GET", "POST"])
def index():
    """Main settings form with basic/advanced tabs."""
    level = request.args.get('level', 'basic')  # Default to basic settings
    
    if request.method == "POST":
        # Handle form submission
        ui_schema = settings_manager.get_web_editable_schema()
        
        for field, schema_info in ui_schema.items():
            if schema_info.get('readonly', False) or not schema_info.get('web_editable', True):
                continue  # Skip read-only or non-web-editable fields
            
            raw_value = request.form.get(field)
            
            # Handle unchecked checkboxes (boolean fields that aren't in form data)
            if raw_value is None:
                if schema_info['type'] == 'bool':
                    # Unchecked checkbox - set to False
                    settings_manager.set(field, False, save=False)
                continue
            
            try:
                # Convert value based on type
                value = convert_form_value(raw_value, schema_info)
                settings_manager.set(field, value, save=False)
            except (ValueError, TypeError) as e:
                # Handle validation errors - could add flash messages here
                print(f"Valideringsfel för {field}: {e}")
                continue
        
        # Save all changes at once
        settings_manager.save_user_settings()
        
        # Flash success message
        flash("Inställningar sparade! Klicka 'Ladda om inställningar' för att aktivera ändringarna.", "success")
        
        return redirect(f"/?level={request.form.get('current_level', 'basic')}")
    
    # GET request - display form
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
        value = raw_value.lower() in ('true', '1', 'on', 'yes')
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
        port = settings_manager.get('Stream.port', 8000)
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
        
        # Get actual FPS if streaming is running
        actual_fps = 0.0
        if is_running:
            try:
                import requests
                response = requests.get(f'http://localhost:{port}/api/info', timeout=2)
                if response.status_code == 200:
                    stream_info = response.json()
                    actual_fps = stream_info.get('actual_fps', 0.0)
            except:
                # Fallback if streaming server API is not available
                actual_fps = 0.0
        
        return jsonify({
            'running': is_running,
            'port': port,
            'url': f"http://{hostname}:{port}",
            'resolution': settings_manager.get('Stream.resolution', [800, 600]),
            'framerate': settings_manager.get('Stream.framerate', 15),
            'actual_fps': actual_fps
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Streaming control removed - now handled by Mode setting


@app.route("/api/settings/reload", methods=["POST"])
def reload_settings():
    """Reload settings without full service restart"""
    try:
        # Write a settings reload request file
        reload_file = "/tmp/cam_reload_settings.txt"
        with open(reload_file, 'w') as f:
            f.write("reload_settings\n")
        
        return jsonify({'success': True, 'message': 'Settings reload requested'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/service/restart", methods=["POST"])
def restart_service():
    """Restart the entire pycam service"""
    try:
        # Write a service restart request file
        reload_file = "/tmp/cam_reload_settings.txt"
        with open(reload_file, 'w') as f:
            f.write("restart_service\n")
        
        return jsonify({'success': True, 'message': 'Service restart requested'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/stream")
def stream_redirect():
    """Redirect to streaming server"""
    port = settings_manager.get('Stream.port', 8000)
    hostname = socket.gethostname()
    return redirect(f"http://{hostname}:{port}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)