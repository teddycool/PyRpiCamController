# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from flask import Flask, render_template, request, redirect
import sys
import os
# Add parent directory to path to access Settings module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Settings.settings_manager import settings_manager

app = Flask(__name__)

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
            if raw_value is None:
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)