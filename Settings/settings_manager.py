# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import json
import os
from typing import Any, Dict, Optional, Union

class SettingsManager:
    """
    Unified settings manager that provides both code interface and web GUI support.
    Single source of truth for all application settings.
    """
    
    def __init__(self, schema_file: str = None, user_file: str = None):
        if schema_file is None:
            # Default to files in same directory as this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            schema_file = os.path.join(script_dir, "settings_schema.json")
        if user_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            user_file = os.path.join(script_dir, "user_settings.json")
            
        self.schema_file = schema_file
        self.user_file = user_file
        self._schema = None
        self._user_settings = {}
        self.load_schema()
        self.load_user_settings()
    
    def load_schema(self):
        """Load the settings schema from JSON file."""
        try:
            with open(self.schema_file, 'r') as f:
                self._schema = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Settings schema file not found: {self.schema_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file: {e}")
    
    def load_user_settings(self):
        """Load user-specific settings overrides."""
        if os.path.exists(self.user_file):
            try:
                with open(self.user_file, 'r') as f:
                    self._user_settings = json.load(f)
            except json.JSONDecodeError:
                self._user_settings = {}
    
    def save_user_settings(self):
        """Save user settings to file."""
        with open(self.user_file, 'w') as f:
            json.dump(self._user_settings, f, indent=2)
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get a nested value using dot notation path."""
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"Path '{path}' not found")
        return current
    
    def _set_nested_value(self, data: Dict, path: str, value: Any):
        """Set a nested value using dot notation path."""
        keys = path.split('.')
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def _get_default_value(self, path: str) -> Any:
        """Get default value from schema."""
        try:
            schema_item = self._get_nested_value(self._schema['settings'], path)
            if isinstance(schema_item, dict) and 'value' in schema_item:
                return schema_item['value']
            else:
                # For nested objects without direct value
                return schema_item
        except KeyError:
            raise KeyError(f"Setting '{path}' not found in schema")
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a setting value by path (e.g., 'Cam.resolution' or 'LogLevel').
        Returns user override if set, otherwise schema default.
        """
        try:
            # Try to get user override first
            return self._get_nested_value(self._user_settings, path)
        except KeyError:
            try:
                # Fall back to schema default
                return self._get_default_value(path)
            except KeyError:
                if default is not None:
                    return default
                raise
    
    def set(self, path: str, value: Any, save: bool = True):
        """Set a setting value and optionally save to file."""
        # Validate against schema if possible
        try:
            schema_item = self._get_nested_value(self._schema['settings'], path)
            if isinstance(schema_item, dict):
                self._validate_value(value, schema_item)
        except KeyError:
            pass  # Setting not in schema, allow it
        
        # Set the value
        self._set_nested_value(self._user_settings, path, value)
        
        if save:
            self.save_user_settings()
    
    def _validate_value(self, value: Any, schema_item: Dict):
        """Validate a value against its schema definition."""
        if 'readonly' in schema_item and schema_item['readonly']:
            raise ValueError(f"Setting is read-only")
        
        setting_type = schema_item.get('type')
        
        if setting_type == 'int':
            if not isinstance(value, int):
                raise TypeError(f"Expected int, got {type(value)}")
            min_val = schema_item.get('min')
            max_val = schema_item.get('max')
            if min_val is not None and value < min_val:
                raise ValueError(f"Value {value} below minimum {min_val}")
            if max_val is not None and value > max_val:
                raise ValueError(f"Value {value} above maximum {max_val}")
        
        elif setting_type == 'float':
            if not isinstance(value, (int, float)):
                raise TypeError(f"Expected float, got {type(value)}")
            min_val = schema_item.get('min')
            max_val = schema_item.get('max')
            if min_val is not None and value < min_val:
                raise ValueError(f"Value {value} below minimum {min_val}")
            if max_val is not None and value > max_val:
                raise ValueError(f"Value {value} above maximum {max_val}")
        
        elif setting_type == 'bool':
            if not isinstance(value, bool):
                raise TypeError(f"Expected bool, got {type(value)}")
        
        elif setting_type == 'enum':
            options = schema_item.get('options', [])
            if value not in options:
                raise ValueError(f"Value '{value}' not in allowed options: {options}")
        
        elif setting_type == 'tuple':
            if not isinstance(value, (list, tuple)):
                raise TypeError(f"Expected tuple/list, got {type(value)}")
    
    def get_all_defaults(self) -> Dict[str, Any]:
        """Get all settings with their default values in flat dictionary format."""
        result = {}
        self._flatten_settings(self._schema['settings'], '', result)
        return result
    
    def _flatten_settings(self, data: Dict, prefix: str, result: Dict):
        """Recursively flatten nested settings into dot notation."""
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                if 'value' in value:
                    # This is a setting with metadata
                    result[current_path] = value['value']
                else:
                    # This is a nested object, recurse
                    self._flatten_settings(value, current_path, result)
    
    def get_ui_schema(self) -> Dict[str, Dict]:
        """Get schema information for UI generation."""
        result = {}
        self._extract_ui_schema(self._schema['settings'], '', result)
        return result
    
    def get_web_editable_schema(self) -> Dict[str, Dict]:
        """Get only settings that are editable via web interface."""
        full_schema = self.get_ui_schema()
        return {key: value for key, value in full_schema.items() 
                if value.get('web_editable', True)}
    
    def _extract_ui_schema(self, data: Dict, prefix: str, result: Dict):
        """Extract UI-relevant schema information."""
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                if 'value' in value:
                    # This is a setting with metadata
                    ui_info = {
                        'type': value.get('type', 'text'),
                        'name': value.get('ui', {}).get('name', key),
                        'section': value.get('ui', {}).get('section', 'General'),
                        'description': value.get('ui', {}).get('description', ''),
                        'default': value['value'],
                        'readonly': value.get('readonly', False),
                        'web_editable': value.get('web_editable', True),
                        'level': value.get('ui', {}).get('level', 'basic')
                    }
                    
                    # Add type-specific constraints
                    if 'min' in value:
                        ui_info['min'] = value['min']
                    if 'max' in value:
                        ui_info['max'] = value['max']
                    if 'options' in value:
                        ui_info['options'] = value['options']
                    
                    result[current_path] = ui_info
                else:
                    # This is a nested object, recurse
                    self._extract_ui_schema(value, current_path, result)
    
    def __getitem__(self, path: str) -> Any:
        """Dictionary-style access for backwards compatibility."""
        return self.get(path)
    
    def __setitem__(self, path: str, value: Any):
        """Dictionary-style setting for backwards compatibility."""
        self.set(path, value)
    
    def get_dict(self):
        """Get all settings as a nested dictionary for backwards compatibility."""
        return SettingsDict(self)


# Backwards compatibility interface that mimics the old defaultsettings dictionary
class SettingsDict:
    """
    Dictionary-like interface for backwards compatibility with existing code.
    Provides the same interface as the old defaultsettings dictionary.
    """
    
    def __init__(self, settings_manager: SettingsManager):
        self._manager = settings_manager
        self._cache = None
        self._build_cache()
    
    def _build_cache(self):
        """Build a nested dictionary cache for efficient access."""
        self._cache = {}
        flat_settings = self._manager.get_all_defaults()
        
        # Apply user overrides
        for path in flat_settings:
            try:
                flat_settings[path] = self._manager.get(path)
            except KeyError:
                pass
        
        # Convert flat dict back to nested
        for path, value in flat_settings.items():
            self._set_nested_dict(self._cache, path, value)
    
    def _set_nested_dict(self, data: Dict, path: str, value: Any):
        """Set value in nested dictionary using dot notation."""
        keys = path.split('.')
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def __getitem__(self, key: str) -> Any:
        if self._cache is None:
            self._build_cache()
        return self._cache[key]
    
    def __contains__(self, key: str) -> bool:
        if self._cache is None:
            self._build_cache()
        return key in self._cache
    
    def get(self, key: str, default: Any = None) -> Any:
        if self._cache is None:
            self._build_cache()
        return self._cache.get(key, default)
    
    def keys(self):
        if self._cache is None:
            self._build_cache()
        return self._cache.keys()
    
    def items(self):
        if self._cache is None:
            self._build_cache()
        return self._cache.items()
    
    def values(self):
        if self._cache is None:
            self._build_cache()
        return self._cache.values()


# Global instances for easy import
settings_manager = SettingsManager()
defaultsettings = SettingsDict(settings_manager)

# For direct access patterns
def get_setting(path: str, default: Any = None) -> Any:
    """Direct function access to settings."""
    return settings_manager.get(path, default)

def set_setting(path: str, value: Any, save: bool = True):
    """Direct function to set settings."""
    settings_manager.set(path, value, save)

if __name__ == "__main__":
    # Example usage
    print("=== Settings Manager Example ===")
    
    # Access like old dictionary
    print(f"Log Level: {defaultsettings['LogLevel']}")
    print(f"Camera Resolution: {defaultsettings['Cam']['resolution']}")
    
    # Access using manager directly
    print(f"Light Level: {settings_manager.get('Light')}")
    print(f"CPU Temp Check: {settings_manager.get('CheckCpuTemp')}")
    
    # Set a value
    settings_manager.set('Light', 75, save=False)
    print(f"New Light Level: {settings_manager.get('Light')}")