#!/usr/bin/env python3
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

"""
Demonstration script showing the unified settings system.
This shows how the same settings work for both code interface and web GUI.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Settings.settings_manager import settings_manager

def demo_code_interface():
    """Demonstrate using settings from Python code (like Main.py does)."""
    print("=== Code Interface Demo ===")
    
    # Reading settings the way Main.py does
    print(f"Log Level: {settings_manager.get('LogLevel')}")
    print(f"Log to Server: {settings_manager.get('LogToServer')}")
    print(f"Camera timeslot: {settings_manager.get('Cam.timeslot')}")
    print(f"Stream port: {settings_manager.get('Stream.port')}")
    print(f"Motion detection enabled: {settings_manager.get('Motion.enabled')}")
    
    # Modify some settings
    print("\nModifying settings...")
    settings_manager.set('LogLevel', 'debug')  # Use lowercase as defined in schema
    settings_manager.set('Cam.timeslot', 15)
    settings_manager.set('Motion.sensitivity', 75)
    
    print(f"New Log Level: {settings_manager.get('LogLevel')}")
    print(f"New Camera timeslot: {settings_manager.get('Cam.timeslot')}")
    print(f"New Motion sensitivity: {settings_manager.get('Motion.sensitivity')}")

def demo_web_gui_data():
    """Demonstrate how the web GUI gets its data structure."""
    print("\n=== Web GUI Data Demo ===")
    
    # Show difference between all settings and web-editable only
    all_ui_schema = settings_manager.get_ui_schema()
    web_ui_schema = settings_manager.get_web_editable_schema()
    
    print(f"Total settings: {len(all_ui_schema)}")
    print(f"Web-editable settings: {len(web_ui_schema)}")
    print(f"Protected settings: {len(all_ui_schema) - len(web_ui_schema)}")
    
    # Show examples of protected settings
    protected_settings = []
    for field, info in all_ui_schema.items():
        if not info.get('web_editable', True):
            protected_settings.append(field)
    
    print(f"\nProtected settings (not editable via web): {protected_settings[:5]}...")
    
    # Group web-editable settings by section (like the web GUI does)
    sections = {}
    for field, info in web_ui_schema.items():
        section = info['section']
        if section not in sections:
            sections[section] = []
        sections[section].append((field, info))
    
    print("\nWeb-editable settings grouped by section:")
    for section_name, fields in sections.items():
        print(f"\n{section_name}:")
        for field_path, field_info in fields[:3]:  # Show first 3 fields per section
            current_value = settings_manager.get(field_path)
            print(f"  {field_info['name']}: {current_value} ({field_info['type']})")
        if len(fields) > 3:
            print(f"    ... and {len(fields) - 3} more editable settings")

def demo_backwards_compatibility():
    """Show how the system maintains backwards compatibility with old code."""
    print("\n=== Backwards Compatibility Demo ===")
    
    # This simulates how old code might access settings
    old_style = settings_manager.get_dict()
    
    print("Old-style dictionary access:")
    print(f"LogLevel: {old_style['LogLevel']}")
    print(f"LogToServer: {old_style['LogToServer']}")
    print(f"Cam settings: {old_style['Cam']}")
    print(f"Nested access: {old_style['Cam']['timeslot']}")

def demo_validation():
    """Demonstrate settings validation."""
    print("\n=== Validation Demo ===")
    
    try:
        # This should work
        settings_manager.set('LogLevel', 'info')  # Use lowercase
        print("✓ Valid LogLevel setting accepted")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    try:
        # This should fail
        settings_manager.set('LogLevel', 'INVALID_LEVEL')
        print("✗ Invalid LogLevel was accepted (this is a bug!)")
    except ValueError as e:
        print(f"✓ Invalid LogLevel rejected: {e}")
    
    try:
        # This should fail
        settings_manager.set('Stream.port', -1)
        print("✗ Invalid port was accepted (this is a bug!)")
    except ValueError as e:
        print(f"✓ Invalid port rejected: {e}")

def demo_web_editable():
    """Demonstrate the web_editable functionality."""
    print("\n=== Web Editable Security Demo ===")
    
    # Show examples of different security levels
    all_schema = settings_manager.get_ui_schema()
    
    examples = {
        'web_editable': [],
        'readonly': [],
        'protected': []
    }
    
    for field, info in all_schema.items():
        if info.get('readonly', False):
            examples['readonly'].append(field)
        elif not info.get('web_editable', True):
            examples['protected'].append(field)
        else:
            examples['web_editable'].append(field)
    
    print(f"✓ Web-editable settings (users can modify): {len(examples['web_editable'])}")
    print(f"  Examples: {examples['web_editable'][:3]}...")
    
    print(f"✓ Protected settings (code-only access): {len(examples['protected'])}")
    print(f"  Examples: {examples['protected'][:3]}...")
    
    print(f"✓ Read-only settings (system values): {len(examples['readonly'])}")
    print(f"  Examples: {examples['readonly'][:3]}...")
    
    # Test that we can still modify protected settings via code
    try:
        # This should work - we can modify protected settings via code
        if 'Mode' in examples['protected']:
            current_mode = settings_manager.get('Mode')
            print(f"✓ Code can read protected setting 'Mode': {current_mode}")
            # Don't actually change it, just show we could access it
    except Exception as e:
        print(f"✗ Error accessing protected setting: {e}")

def main():
    """Run all demonstrations."""
    print("Unified Settings System Demonstration")
    print("=====================================")
    print("This shows how the SAME settings structure serves both:")
    print("1. Python code interface (like Main.py)")
    print("2. Web GUI forms (like settings_form.html)")
    print()
    
    # Initialize settings system
    print("Loading settings...")
    try:
        demo_code_interface()
        demo_web_gui_data()
        demo_backwards_compatibility()
        demo_validation()
        demo_web_editable()
        
        print("\n=== Summary ===")
        print("✓ Single JSON schema defines all settings")
        print("✓ Python code uses simple dot notation (settings_manager.get('Cam.timeslot'))")
        print("✓ Web GUI auto-generates forms from same schema")
        print("✓ Security: web_editable flag controls web interface access")
        print("✓ Backwards compatibility maintained with old code")
        print("✓ Validation ensures data integrity")
        print("✓ Changes saved to user_settings.json override defaults")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()