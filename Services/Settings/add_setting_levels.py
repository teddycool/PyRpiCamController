#!/usr/bin/env python3
"""
Helper script to add 'level' property to all settings in the schema.
This script categorizes settings into 'basic' and 'advanced' levels.
"""

import json
import sys

def categorize_setting(setting_name, ui_info):
    """Determine if a setting should be basic or advanced based on its properties."""
    name = ui_info.get('name', '').lower()
    section = ui_info.get('section', '').lower()
    description = ui_info.get('description', '').lower()
    
    # Basic settings - commonly used camera controls
    basic_keywords = [
        'kameraläge', 'mode',  # Camera mode
        'bildupplösning', 'resolution',  # Image resolution
        'bildintervall', 'interval',  # Image interval
        'publicera', 'publish',  # Publishing controls
        'spara', 'save', 'fil',  # File saving
        'url', 'location',  # Basic publishing settings
        'beskär', 'crop',  # Basic cropping
        'exponering', 'exposure'  # Basic exposure
    ]
    
    # Advanced settings - technical/system settings
    advanced_keywords = [
        'version', 'schema',  # Version info
        'ota', 'uppdatering',  # OTA updates
        'api', 'nyckel', 'key',  # API keys
        'timeout', 'tjänst', 'service',  # System services
        'installation', 'backup',  # Installation settings
        'rörelsedetektor', 'motion', 'history',  # Motion detection details
        'nedladdning', 'download',  # Download settings
        'hälsokontroll', 'health'  # Health checks
    ]
    
    # Check if setting is web_editable - non-editable are usually advanced
    if 'web_editable' in ui_info.get('..', {}) and not ui_info['..'].get('web_editable', True):
        return 'advanced'
    
    # Check section - System section is usually advanced
    if 'system' in section:
        # But some system settings might be basic
        for keyword in basic_keywords:
            if keyword in name or keyword in description:
                return 'basic'
        return 'advanced'
    
    # Check for basic keywords first
    for keyword in basic_keywords:
        if keyword in name or keyword in description:
            return 'basic'
    
    # Check for advanced keywords
    for keyword in advanced_keywords:
        if keyword in name or keyword in description:
            return 'advanced'
    
    # Default camera settings to basic if not clearly advanced
    if 'kamera' in section or 'camera' in section:
        return 'basic'
    
    # Default to advanced for unclear cases
    return 'advanced'

def add_level_to_settings(schema):
    """Add level property to all settings in the schema."""
    updated_count = 0
    
    def process_settings_recursive(obj, path=""):
        nonlocal updated_count
        
        if isinstance(obj, dict):
            # Check if this is a setting with UI info
            if 'ui' in obj and isinstance(obj['ui'], dict):
                if 'level' not in obj['ui']:
                    level = categorize_setting(path, obj['ui'])
                    obj['ui']['level'] = level
                    updated_count += 1
                    print(f"Added level '{level}' to: {path} ({obj['ui'].get('name', 'unnamed')})")
            
            # Recursively process nested objects
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                process_settings_recursive(value, new_path)
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                process_settings_recursive(item, f"{path}[{i}]")
    
    # Process the settings section
    if 'settings' in schema:
        process_settings_recursive(schema['settings'])
    
    return updated_count

def main():
    input_file = 'settings_schema.json'
    
    # Read the current schema
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found!")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return 1
    
    print(f"Processing {input_file}...")
    
    # Add level properties
    updated_count = add_level_to_settings(schema)
    
    if updated_count > 0:
        # Write back to file
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully updated {updated_count} settings with level properties")
    else:
        print("No settings needed level property updates")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())