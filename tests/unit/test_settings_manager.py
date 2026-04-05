# Unit tests for SettingsManager
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import pytest
import os
import tempfile
import json
import shutil
import sys

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'Settings'))

from settings_manager import SettingsManager

class TestSettingsManager:
    """Test cases for SettingsManager with storage management settings."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_schema_path = os.path.join(self.temp_dir, "test_schema.json")
        self.test_user_path = os.path.join(self.temp_dir, "test_user.json")
        
        # Create test schema with storage management settings
        self.test_schema = {
            "schema_version": "1.0",
            "settings": {
                "Cam": {
                    "format": {
                        "value": "jpg",
                        "type": "enum",
                        "options": ["jpg", "png"]
                    },
                    "publishers": {
                        "file": {
                            "publish": {
                                "value": True,
                                "type": "bool"
                            },
                            "location": {
                                "value": "/tmp/images",
                                "type": "text"
                            }
                        }
                    },
                    "storage_management": {
                        "enabled": {
                            "value": True,
                            "type": "bool"
                        },
                        "mode": {
                            "value": "delete_old",
                            "type": "enum",
                            "options": ["stop_saving", "delete_old"]
                        },
                        "threshold_value": {
                            "value": 100,
                            "type": "int",
                            "min": 50,
                            "max": 10000
                        },
                        "threshold_unit": {
                            "value": "MB",
                            "type": "enum", 
                            "options": ["MB", "percent"]
                        }
                    }
                }
            }
        }
        
        # Write test schema
        with open(self.test_schema_path, 'w') as f:
            json.dump(self.test_schema, f)

    def teardown_method(self):
        """Cleanup after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_schema_with_storage_settings(self):
        """Test loading schema that includes storage management settings."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Check that storage management settings are loaded
        storage_settings = manager._schema["settings"]["Cam"]["storage_management"]
        
        assert "enabled" in storage_settings
        assert "mode" in storage_settings
        assert "threshold_value" in storage_settings
        assert "threshold_unit" in storage_settings
        
        assert storage_settings["enabled"]["value"] == True
        assert storage_settings["mode"]["value"] == "delete_old"
        assert storage_settings["threshold_value"]["value"] == 100
        assert storage_settings["threshold_unit"]["value"] == "MB"

    def test_get_storage_management_settings(self):
        """Test getting storage management settings through the manager."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Test getting nested settings
        enabled = manager.get("Cam.storage_management.enabled", False)
        mode = manager.get("Cam.storage_management.mode", "stop_saving")
        threshold_value = manager.get("Cam.storage_management.threshold_value", 500)
        threshold_unit = manager.get("Cam.storage_management.threshold_unit", "MB")
        
        assert enabled == True
        assert mode == "delete_old"
        assert threshold_value == 100
        assert threshold_unit == "MB"

    def test_set_storage_management_settings(self):
        """Test setting storage management settings through the manager."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Update settings
        manager.set("Cam.storage_management.enabled", False)
        manager.set("Cam.storage_management.mode", "stop_saving")
        manager.set("Cam.storage_management.threshold_value", 200)
        manager.set("Cam.storage_management.threshold_unit", "percent")
        
        # Verify changes
        assert manager.get("Cam.storage_management.enabled") == False
        assert manager.get("Cam.storage_management.mode") == "stop_saving"
        assert manager.get("Cam.storage_management.threshold_value") == 200
        assert manager.get("Cam.storage_management.threshold_unit") == "percent"

    def test_user_settings_override_storage_defaults(self):
        """Test that user settings override storage management defaults."""
        # Create user settings that override defaults
        user_settings = {
            "Cam": {
                "storage_management": {
                    "enabled": False,
                    "threshold_value": 50
                }
            }
        }
        
        with open(self.test_user_path, 'w') as f:
            json.dump(user_settings, f)
        
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Should use user overrides
        assert manager.get("Cam.storage_management.enabled") == False
        assert manager.get("Cam.storage_management.threshold_value") == 50
        
        # Should use schema defaults for non-overridden settings
        assert manager.get("Cam.storage_management.mode") == "delete_old"
        assert manager.get("Cam.storage_management.threshold_unit") == "MB"

    def test_validate_storage_mode_enum(self):
        """Test validation of storage mode enum values."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Valid values should work
        manager.set("Cam.storage_management.mode", "stop_saving")
        assert manager.get("Cam.storage_management.mode") == "stop_saving"
        
        manager.set("Cam.storage_management.mode", "delete_old")
        assert manager.get("Cam.storage_management.mode") == "delete_old"

    def test_validate_threshold_unit_enum(self):
        """Test validation of threshold unit enum values."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Valid values should work
        manager.set("Cam.storage_management.threshold_unit", "MB")
        assert manager.get("Cam.storage_management.threshold_unit") == "MB"
        
        manager.set("Cam.storage_management.threshold_unit", "percent")
        assert manager.get("Cam.storage_management.threshold_unit") == "percent"

    def test_validate_threshold_value_range(self):
        """Test validation of threshold value range."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Valid values within range should work
        manager.set("Cam.storage_management.threshold_value", 75)
        assert manager.get("Cam.storage_management.threshold_value") == 75
        
        manager.set("Cam.storage_management.threshold_value", 1000)
        assert manager.get("Cam.storage_management.threshold_value") == 1000

    def test_get_flat_settings_for_file_publisher(self):
        """Test getting flattened settings structure for FilePublisher."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Get settings in the format FilePublisher expects
        cam_settings = manager.get_dict()["Cam"]
        
        # Should have the nested structure
        assert "publishers" in cam_settings
        assert "file" in cam_settings["publishers"]
        assert "storage_management" in cam_settings
        
        # Check file publisher settings
        file_settings = cam_settings["publishers"]["file"]
        assert file_settings["publish"] == True
        assert file_settings["location"] == "/tmp/images"
        assert cam_settings["format"] == "jpg"
        
        # Check storage management settings
        storage_settings = cam_settings["storage_management"]
        assert storage_settings["enabled"] == True
        assert storage_settings["mode"] == "delete_old"
        assert storage_settings["threshold_value"] == 100
        assert storage_settings["threshold_unit"] == "MB"

    def test_save_and_load_storage_settings(self):
        """Test saving and loading storage management settings."""
        manager = SettingsManager(self.test_schema_path, self.test_user_path)
        
        # Modify storage settings
        manager.set("Cam.storage_management.enabled", False)
        manager.set("Cam.storage_management.mode", "stop_saving")
        manager.set("Cam.storage_management.threshold_value", 250)
        
        # Save settings
        manager.save_settings()
        
        # Create new manager instance and verify persistence
        manager2 = SettingsManager(self.test_schema_path, self.test_user_path)
        
        assert manager2.get("Cam.storage_management.enabled") == False
        assert manager2.get("Cam.storage_management.mode") == "stop_saving"
        assert manager2.get("Cam.storage_management.threshold_value") == 250
        assert manager2.get("Cam.storage_management.threshold_unit") == "MB"  # Default

    def test_missing_storage_settings_use_defaults(self):
        """Test that missing storage settings use reasonable defaults."""
        # Create minimal schema without storage management
        minimal_schema = {
            "schema_version": "1.0", 
            "settings": {
                "Cam": {
                    "publishers": {
                        "file": {
                            "publish": {"value": True, "type": "bool"}
                        }
                    }
                }
            }
        }
        
        minimal_schema_path = os.path.join(self.temp_dir, "minimal_schema.json")
        with open(minimal_schema_path, 'w') as f:
            json.dump(minimal_schema, f)
        
        manager = SettingsManager(minimal_schema_path, self.test_user_path)
        
        # Should return defaults for missing storage settings
        assert manager.get("Cam.storage_management.enabled", True) == True
        assert manager.get("Cam.storage_management.mode", "delete_old") == "delete_old"
        assert manager.get("Cam.storage_management.threshold_value", 500) == 500
        assert manager.get("Cam.storage_management.threshold_unit", "MB") == "MB"

if __name__ == "__main__":
    pytest.main([__file__])