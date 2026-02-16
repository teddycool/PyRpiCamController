# Additional test utilities for edge cases
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import pytest
import os
import tempfile
import shutil
import json
from unittest.mock import patch, MagicMock
import sys

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'CamController'))

from Publishers.FilePublisher import FilePublisher
from tests.utils.mock_helpers import MockFileSystem

class TestFilePublisherEdgeCases:
    """Test edge cases and error conditions for FilePublisher."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.test_settings = {
            "Cam": {
                "publishers": {
                    "file": {
                        "location": self.temp_dir,
                        "format": "jpg"
                    }
                },
                "storage_management": {
                    "enabled": True,
                    "mode": "delete_old",
                    "threshold_value": 100,
                    "threshold_unit": "MB"
                }
            }
        }

    def teardown_method(self):
        """Cleanup after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_permission_denied_during_file_deletion(self):
        """Test behavior when file deletion fails due to permissions."""
        publisher = FilePublisher()
        publisher.initialize(self.test_settings)
        
        # Create test files
        file_system = MockFileSystem(self.temp_dir)
        file_system.create_test_files(3)
        
        # Mock os.remove to raise PermissionError
        with patch('os.remove', side_effect=PermissionError("Permission denied")):
            with patch('shutil.disk_usage', return_value=(1000*1024*1024, 950*1024*1024, 50*1024*1024)):
                deleted_count = publisher.delete_old_files()
                
                # Should handle permission errors gracefully
                assert deleted_count == 0  # No files deleted due to permission error

    def test_directory_does_not_exist(self):
        """Test behavior when image directory doesn't exist."""
        non_existent_dir = "/tmp/non_existent_directory_12345"
        
        settings = {
            "Cam": {
                "publishers": {
                    "file": {
                        "location": non_existent_dir,
                        "format": "jpg"
                    }
                },
                "storage_management": {
                    "enabled": True,
                    "mode": "delete_old", 
                    "threshold_value": 100,
                    "threshold_unit": "MB"
                }
            }
        }
        
        publisher = FilePublisher()
        
        # Should create directory during initialization
        publisher.initialize(settings)
        assert os.path.exists(non_existent_dir)
        
        # Clean up
        shutil.rmtree(non_existent_dir, ignore_errors=True)

    def test_corrupted_metadata_files(self):
        """Test behavior with corrupted or invalid JSON metadata files."""
        publisher = FilePublisher()
        publisher.initialize(self.test_settings)
        
        # Create valid image file and corrupted metadata file
        img_path = os.path.join(self.temp_dir, "1234567890.jpg")
        meta_path = os.path.join(self.temp_dir, "1234567890.json")
        
        with open(img_path, 'wb') as f:
            f.write(b'fake_image_data')
        
        with open(meta_path, 'w') as f:
            f.write('invalid json content {')
        
        # Should handle corrupted files gracefully
        old_files = publisher.get_old_files()
        assert len(old_files) > 0  # Should still find files despite corruption

    def test_disk_full_during_write(self):
        """Test behavior when disk becomes full during file write."""
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage', return_value=(1000*1024*1024, 900*1024*1024, 100*1024*1024)):
            publisher.initialize(self.test_settings)
            
            # Mock file write to raise OSError (disk full)
            with patch('builtins.open', side_effect=OSError("No space left on device")):
                image_data = bytearray([0xFF, 0xD8] + [0x00] * 100 + [0xFF, 0xD9])
                metadata = {"timestamp": 1234567890}
                
                # Should handle disk full error gracefully
                publisher.publish(image_data, metadata)
                
                # No files should be created
                files = os.listdir(self.temp_dir)
                assert len(files) == 0

    def test_extremely_low_threshold_values(self):
        """Test behavior with very low threshold values."""
        # Test with 1MB threshold
        self.test_settings["Cam"]["storage_management"]["threshold_value"] = 1
        
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage', return_value=(1000*1024*1024, 999*1024*1024, 1*1024*1024)):
            publisher.initialize(self.test_settings)
            
            # Should detect low space even with tiny threshold
            assert publisher.is_disk_space_low() == False  # 1MB free >= 1MB threshold

    def test_zero_threshold_value(self):
        """Test behavior with zero threshold value."""
        self.test_settings["Cam"]["storage_management"]["threshold_value"] = 0
        
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage', return_value=(1000*1024*1024, 1000*1024*1024, 0)):
            publisher.initialize(self.test_settings)
            
            # Should never detect low space with zero threshold
            assert publisher.is_disk_space_low() == False

    def test_percentage_threshold_edge_cases(self):
        """Test percentage threshold at boundary values."""
        self.test_settings["Cam"]["storage_management"]["threshold_unit"] = "percent"
        
        publisher = FilePublisher()
        
        # Test 0% threshold
        self.test_settings["Cam"]["storage_management"]["threshold_value"] = 0
        publisher.initialize(self.test_settings)
        
        with patch('shutil.disk_usage', return_value=(1000*1024*1024, 1000*1024*1024, 0)):
            assert publisher.is_disk_space_low() == False  # 0% free >= 0% threshold
        
        # Test 100% threshold  
        self.test_settings["Cam"]["storage_management"]["threshold_value"] = 100
        publisher.initialize(self.test_settings)
        
        with patch('shutil.disk_usage', return_value=(1000*1024*1024, 0, 1000*1024*1024)):
            assert publisher.is_disk_space_low() == False  # 100% free >= 100% threshold

    def test_no_old_files_to_delete_in_delete_mode(self):
        """Test delete_old mode when there are no files to delete."""
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage', return_value=(1000*1024*1024, 950*1024*1024, 50*1024*1024)):
            publisher.initialize(self.test_settings)
            
            # No files in directory
            result = publisher.manage_storage_space()
            
            # Should return False since no space could be freed
            assert result == False

    @patch('CamController.Publishers.FilePublisher.logger')
    def test_logging_during_storage_operations(self, mock_logger):
        """Test that appropriate log messages are generated during storage operations."""
        publisher = FilePublisher()
        
        with patch('shutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.side_effect = [
                (1000*1024*1024, 950*1024*1024, 50*1024*1024),  # Low space
                (1000*1024*1024, 900*1024*1024, 100*1024*1024), # OK after deletion
            ]
            
            publisher.initialize(self.test_settings)
            
            # Create files to delete
            file_system = MockFileSystem(self.temp_dir)
            file_system.create_test_files(5)
            
            # Trigger storage management
            publisher.manage_storage_space()
            
            # Verify appropriate log messages
            mock_logger.warning.assert_called()  # Should warn about low space
            mock_logger.info.assert_called()     # Should info about cleanup

    def test_invalid_image_format_setting(self):
        """Test behavior with invalid image format in settings."""
        self.test_settings["Cam"]["publishers"]["file"]["format"] = "invalid_format"
        
        publisher = FilePublisher()
        
        # Should raise ValueError for invalid format
        with pytest.raises(ValueError, match="Unsupported image format"):
            publisher.initialize(self.test_settings)

if __name__ == "__main__":
    pytest.main([__file__])