# Integration tests for storage management system
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import pytest
import os
import tempfile
import shutil
import json
import time
from unittest.mock import patch, MagicMock
import sys

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'CamController'))
sys.path.insert(0, os.path.join(project_root, 'Settings'))

from Publishers.FilePublisher import FilePublisher
from settings_manager import SettingsManager
from tests.utils.mock_helpers import MockFileSystem

class TestStorageManagementIntegration:
    """Integration tests for the complete storage management system."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.schema_path = os.path.join(self.temp_dir, "schema.json")
        self.user_path = os.path.join(self.temp_dir, "user.json")
        self.image_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(self.image_dir)
        
        # Create test schema
        self.create_test_schema()
        
        # Create settings manager
        self.settings_manager = SettingsManager(self.schema_path, self.user_path)

    def teardown_method(self):
        """Cleanup after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_schema(self):
        """Create a complete test schema with storage management."""
        schema = {
            "schema_version": "1.0",
            "settings": {
                "Cam": {
                    "publishers": {
                        "file": {
                            "publish": {"value": True, "type": "bool"},
                            "location": {"value": self.image_dir, "type": "text"},
                            "format": {"value": "jpg", "type": "enum", "options": ["jpg"]}
                        }
                    },
                    "storage_management": {
                        "enabled": {"value": True, "type": "bool"},
                        "mode": {"value": "delete_old", "type": "enum", "options": ["stop_saving", "delete_old"]},
                        "threshold_value": {"value": 50, "type": "int", "min": 10, "max": 1000},
                        "threshold_unit": {"value": "MB", "type": "enum", "options": ["MB", "percent"]}
                    }
                }
            }
        }
        
        with open(self.schema_path, 'w') as f:
            json.dump(schema, f)

    def test_end_to_end_storage_management_delete_mode(self):
        """Test complete workflow: settings -> FilePublisher -> storage management in delete mode."""
        
        # Step 1: Get settings from manager
        settings = {"Cam": self.settings_manager.get("Cam")}
        
        # Step 2: Initialize FilePublisher with settings
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            # Simulate low disk space scenario
            mock_disk_usage.side_effect = [
                (1000*1024*1024, 960*1024*1024, 40*1024*1024),  # 40MB free (below 50MB threshold)
                (1000*1024*1024, 900*1024*1024, 100*1024*1024), # 100MB free (after deletion)
                (1000*1024*1024, 900*1024*1024, 100*1024*1024), # Still good
            ]
            
            publisher.initialize(settings)
            
            # Step 3: Create some old files to be deleted
            file_system = MockFileSystem(self.image_dir)
            old_files = file_system.create_test_files(10)  # 20 files total (10 images + 10 metadata)
            
            initial_count = file_system.get_file_count()
            assert initial_count == 20
            
            # Step 4: Publish a new image (should trigger cleanup)
            image_data = bytearray([0xFF, 0xD8] + [0x00] * 100 + [0xFF, 0xD9])
            metadata = {"timestamp": int(time.time()), "test": "integration"}
            
            publisher.publish(image_data, metadata)
            
            # Step 5: Verify results
            final_count = file_system.get_file_count()
            
            # Should have deleted some old files and added new ones
            assert final_count < initial_count + 2  # Some old files deleted
            assert final_count >= 2  # At least the new image and metadata
            
            # Verify new files exist
            files = os.listdir(self.image_dir)
            jpg_files = [f for f in files if f.endswith('.jpg')]
            json_files = [f for f in files if f.endswith('.json')]
            
            assert len(jpg_files) >= 1
            assert len(json_files) >= 1

    def test_end_to_end_storage_management_stop_mode(self):
        """Test complete workflow with stop_saving mode."""
        
        # Update settings to use stop_saving mode
        self.settings_manager.set("Cam.storage_management.mode", "stop_saving")
        settings = {"Cam": self.settings_manager.get("Cam")}
        
        # Initialize FilePublisher
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            # Simulate low disk space
            mock_disk_usage.return_value = (1000*1024*1024, 960*1024*1024, 40*1024*1024)  # 40MB free
            
            publisher.initialize(settings)
            
            # Try to publish (should be rejected)
            image_data = bytearray([0xFF, 0xD8] + [0x00] * 100 + [0xFF, 0xD9])
            metadata = {"timestamp": int(time.time())}
            
            publisher.publish(image_data, metadata)
            
            # Verify no files were created
            files = os.listdir(self.image_dir)
            assert len(files) == 0

    def test_settings_changes_affect_publisher_behavior(self):
        """Test that changing settings affects FilePublisher behavior."""
        
        # Start with delete_old mode
        settings = {"Cam": self.settings_manager.get("Cam")}
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.return_value = (1000*1024*1024, 960*1024*1024, 40*1024*1024)  # Low space
            
            publisher.initialize(settings)
            assert publisher.storage_mode == "delete_old"
            
            # Create old files
            file_system = MockFileSystem(self.image_dir)
            file_system.create_test_files(5)
            
            # Should allow publishing (will delete old files)
            result = publisher.manage_storage_space()
            # Note: Result depends on whether deletion freed enough space
            
            # Now change to stop_saving mode
            self.settings_manager.set("Cam.storage_management.mode", "stop_saving")
            updated_settings = {"Cam": self.settings_manager.get("Cam")}
            
            # Create new publisher with updated settings
            publisher2 = FilePublisher()
            publisher2.initialize(updated_settings)
            assert publisher2.storage_mode == "stop_saving"
            
            # Should refuse to save
            result2 = publisher2.manage_storage_space()
            assert result2 == False

    def test_different_threshold_units_behave_correctly(self):
        """Test that MB and percentage thresholds work correctly."""
        
        # Test MB threshold
        settings = {"Cam": self.settings_manager.get("Cam")}
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            # 1GB total, 40MB free (below 50MB threshold)
            mock_disk_usage.return_value = (1000*1024*1024, 960*1024*1024, 40*1024*1024)
            
            publisher.initialize(settings)
            assert publisher.is_disk_space_low() == True
            
            # 60MB free (above 50MB threshold)
            mock_disk_usage.return_value = (1000*1024*1024, 940*1024*1024, 60*1024*1024)
            assert publisher.is_disk_space_low() == False
        
        # Test percentage threshold
        self.settings_manager.set("Cam.storage_management.threshold_unit", "percent")
        self.settings_manager.set("Cam.storage_management.threshold_value", 10)  # 10%
        
        settings = {"Cam": self.settings_manager.get("Cam")}
        publisher2 = FilePublisher()
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            # 1GB total, 50MB free (5% free - below 10% threshold)
            mock_disk_usage.return_value = (1000*1024*1024, 950*1024*1024, 50*1024*1024)
            
            publisher2.initialize(settings)
            assert publisher2.is_disk_space_low() == True
            
            # 1GB total, 150MB free (15% free - above 10% threshold)
            mock_disk_usage.return_value = (1000*1024*1024, 850*1024*1024, 150*1024*1024)
            assert publisher2.is_disk_space_low() == False

    def test_disabled_storage_management_allows_all_operations(self):
        """Test that disabling storage management allows all operations regardless of disk space."""
        
        # Disable storage management
        self.settings_manager.set("Cam.storage_management.enabled", False)
        settings = {"Cam": self.settings_manager.get("Cam")}
        
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            # Simulate extremely low disk space
            mock_disk_usage.return_value = (1000*1024*1024, 999*1024*1024, 1*1024*1024)  # 1MB free
            
            publisher.initialize(settings)
            
            # Should still allow operations
            assert publisher.is_disk_space_low() == False
            assert publisher.manage_storage_space() == True
            
            # Should be able to publish
            image_data = bytearray([0xFF, 0xD8] + [0x00] * 100 + [0xFF, 0xD9])
            metadata = {"timestamp": int(time.time())}
            
            publisher.publish(image_data, metadata)
            
            # Verify files were created
            files = os.listdir(self.image_dir)
            jpg_files = [f for f in files if f.endswith('.jpg')]
            json_files = [f for f in files if f.endswith('.json')]
            
            assert len(jpg_files) == 1
            assert len(json_files) == 1

    def test_persistence_of_settings_across_restarts(self):
        """Test that storage management settings persist across application restarts."""
        
        # Modify settings
        self.settings_manager.set("Cam.storage_management.enabled", False)
        self.settings_manager.set("Cam.storage_management.mode", "stop_saving")
        self.settings_manager.set("Cam.storage_management.threshold_value", 200)
        self.settings_manager.set("Cam.storage_management.threshold_unit", "percent")
        
        # Save settings
        self.settings_manager.save_settings()
        
        # Simulate application restart
        new_settings_manager = SettingsManager(self.schema_path, self.user_path)
        
        # Verify persistence
        assert new_settings_manager.get("Cam.storage_management.enabled") == False
        assert new_settings_manager.get("Cam.storage_management.mode") == "stop_saving"
        assert new_settings_manager.get("Cam.storage_management.threshold_value") == 200
        assert new_settings_manager.get("Cam.storage_management.threshold_unit") == "percent"
        
        # Create FilePublisher with persisted settings
        settings = {"Cam": new_settings_manager.get("Cam")}
        publisher = FilePublisher()
        publisher.initialize(settings)
        
        # Verify FilePublisher uses persisted settings
        assert publisher.storage_enabled == False
        assert publisher.storage_mode == "stop_saving"
        assert publisher.threshold_value == 200
        assert publisher.threshold_unit == "percent"

if __name__ == "__main__":
    pytest.main([__file__])