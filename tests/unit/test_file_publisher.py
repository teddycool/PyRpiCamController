# Unit tests for FilePublisher disk space management
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import pytest
import os
import tempfile
import shutil
import time
from unittest.mock import MagicMock, patch, mock_open
import sys

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'CamController'))

from Publishers.FilePublisher import FilePublisher
from tests.utils.mock_helpers import MockDiskUsage, MockFileSystem, create_mock_logger

class TestFilePublisherDiskManagement:
    """Test cases for FilePublisher disk space management features."""

    def setup_method(self):
        """Setup for each test method."""
        self.publisher = FilePublisher()
        self.temp_dir = tempfile.mkdtemp()
        
        # Default test settings
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

    def test_initialize_with_storage_settings(self):
        """Test FilePublisher initialization with storage management settings."""
        self.publisher.initialize(self.test_settings)
        
        assert self.publisher.location == self.temp_dir
        assert self.publisher.storage_enabled == True
        assert self.publisher.storage_mode == "delete_old"
        assert self.publisher.threshold_value == 100
        assert self.publisher.threshold_unit == "MB"

    def test_initialize_with_default_settings(self):
        """Test FilePublisher initialization with default storage settings."""
        minimal_settings = {
            "Cam": {
                "publishers": {
                    "file": {
                        "location": self.temp_dir,
                        "format": "jpg"
                    }
                }
            }
        }
        
        self.publisher.initialize(minimal_settings)
        
        # Should use defaults
        assert self.publisher.storage_enabled == True
        assert self.publisher.storage_mode == "delete_old"
        assert self.publisher.threshold_value == 500
        assert self.publisher.threshold_unit == "MB"

    @patch('shutil.disk_usage')
    def test_get_disk_usage(self, mock_disk_usage):
        """Test disk usage retrieval."""
        mock_disk_usage.return_value = (1000000000, 800000000, 200000000)  # 1GB total, 200MB free
        
        self.publisher.initialize(self.test_settings)
        total, used, free = self.publisher.get_disk_usage(self.temp_dir)
        
        assert total == 1000000000
        assert used == 800000000
        assert free == 200000000

    @patch('shutil.disk_usage')
    def test_get_disk_usage_error(self, mock_disk_usage):
        """Test disk usage when there's an error."""
        mock_disk_usage.side_effect = OSError("Permission denied")
        
        self.publisher.initialize(self.test_settings)
        total, used, free = self.publisher.get_disk_usage(self.temp_dir)
        
        assert total == 0
        assert used == 0
        assert free == 0

    @patch('shutil.disk_usage')
    def test_is_disk_space_low_mb_threshold(self, mock_disk_usage):
        """Test disk space check with MB threshold."""
        # 50MB free, threshold is 100MB -> should be low
        mock_disk_usage.return_value = (1000000000, 950000000, 50*1024*1024)
        
        self.publisher.initialize(self.test_settings)
        assert self.publisher.is_disk_space_low() == True
        
        # 150MB free, threshold is 100MB -> should be OK
        mock_disk_usage.return_value = (1000000000, 850000000, 150*1024*1024)
        assert self.publisher.is_disk_space_low() == False

    @patch('shutil.disk_usage')
    def test_is_disk_space_low_percent_threshold(self, mock_disk_usage):
        """Test disk space check with percentage threshold."""
        # Set to 10% threshold
        self.test_settings["Cam"]["storage_management"]["threshold_unit"] = "percent"
        self.test_settings["Cam"]["storage_management"]["threshold_value"] = 10
        
        # 5% free (50MB of 1GB) -> should be low
        mock_disk_usage.return_value = (1000*1024*1024, 950*1024*1024, 50*1024*1024)
        
        self.publisher.initialize(self.test_settings)
        assert self.publisher.is_disk_space_low() == True
        
        # 15% free (150MB of 1GB) -> should be OK
        mock_disk_usage.return_value = (1000*1024*1024, 850*1024*1024, 150*1024*1024)
        assert self.publisher.is_disk_space_low() == False

    def test_is_disk_space_low_disabled(self):
        """Test that disk space check returns False when storage management is disabled."""
        self.test_settings["Cam"]["storage_management"]["enabled"] = False
        
        self.publisher.initialize(self.test_settings)
        assert self.publisher.is_disk_space_low() == False

    def test_get_old_files(self):
        """Test getting list of old files sorted by age."""
        self.publisher.initialize(self.test_settings)
        
        # Create test files with different timestamps
        base_time = int(time.time()) - 10000
        file_system = MockFileSystem(self.temp_dir)
        created_files = file_system.create_test_files(3, base_time)
        
        old_files = self.publisher.get_old_files()
        
        # Should return files sorted by modification time (oldest first)
        assert len(old_files) == 6  # 3 images + 3 metadata files
        
        # Check that files are sorted correctly
        timestamps = [f[1] for f in old_files]
        assert timestamps == sorted(timestamps)

    def test_get_old_files_empty_directory(self):
        """Test getting old files from an empty directory."""
        self.publisher.initialize(self.test_settings)
        
        old_files = self.publisher.get_old_files()
        assert len(old_files) == 0

    @patch('shutil.disk_usage')
    def test_delete_old_files(self, mock_disk_usage):
        """Test deletion of old files."""
        # Setup: low disk space initially, then OK after deletion
        mock_disk_usage.side_effect = [
            (1000*1024*1024, 950*1024*1024, 50*1024*1024),  # Low space initially
            (1000*1024*1024, 850*1024*1024, 150*1024*1024), # OK after deletion
        ]
        
        self.publisher.initialize(self.test_settings)
        
        # Create test files
        file_system = MockFileSystem(self.temp_dir)
        created_files = file_system.create_test_files(5)
        initial_count = file_system.get_file_count()
        
        deleted_count = self.publisher.delete_old_files()
        
        # Should have deleted some files
        assert deleted_count > 0
        final_count = file_system.get_file_count()
        assert final_count < initial_count

    @patch('shutil.disk_usage') 
    def test_manage_storage_space_stop_saving_mode(self, mock_disk_usage):
        """Test storage management in stop_saving mode."""
        mock_disk_usage.return_value = (1000*1024*1024, 950*1024*1024, 50*1024*1024)  # Low space
        
        self.test_settings["Cam"]["storage_management"]["mode"] = "stop_saving"
        self.publisher.initialize(self.test_settings)
        
        result = self.publisher.manage_storage_space()
        assert result == False  # Should refuse to save

    @patch('shutil.disk_usage')
    def test_manage_storage_space_delete_old_mode(self, mock_disk_usage):
        """Test storage management in delete_old mode."""
        mock_disk_usage.side_effect = [
            (1000*1024*1024, 950*1024*1024, 50*1024*1024),  # Low space initially
            (1000*1024*1024, 850*1024*1024, 150*1024*1024), # OK after deletion
            (1000*1024*1024, 850*1024*1024, 150*1024*1024), # Still OK
        ]
        
        self.publisher.initialize(self.test_settings)
        
        # Create old files to delete
        file_system = MockFileSystem(self.temp_dir)
        file_system.create_test_files(5)
        
        result = self.publisher.manage_storage_space()
        assert result == True  # Should allow saving after cleanup

    @patch('shutil.disk_usage')
    def test_manage_storage_space_sufficient_space(self, mock_disk_usage):
        """Test storage management when there's sufficient space."""
        mock_disk_usage.return_value = (1000*1024*1024, 850*1024*1024, 150*1024*1024)  # Plenty of space
        
        self.publisher.initialize(self.test_settings)
        
        result = self.publisher.manage_storage_space()
        assert result == True  # Should allow saving

    def test_manage_storage_space_disabled(self):
        """Test storage management when disabled."""
        self.test_settings["Cam"]["storage_management"]["enabled"] = False
        self.publisher.initialize(self.test_settings)
        
        result = self.publisher.manage_storage_space()
        assert result == True  # Should always allow saving when disabled

    @patch('shutil.disk_usage')
    @patch('CamController.Publishers.FilePublisher.logger')
    def test_publish_with_sufficient_space(self, mock_logger, mock_disk_usage):
        """Test normal publish operation with sufficient disk space."""
        mock_disk_usage.return_value = (1000*1024*1024, 850*1024*1024, 150*1024*1024)  # Plenty of space
        
        self.publisher.initialize(self.test_settings)
        
        # Sample image data
        image_data = bytearray([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 100 + [0xFF, 0xD9])
        metadata = {"timestamp": int(time.time())}
        
        self.publisher.publish(image_data, metadata)
        
        # Should create files
        files = os.listdir(self.temp_dir)
        jpg_files = [f for f in files if f.endswith('.jpg')]
        json_files = [f for f in files if f.endswith('.json')]
        
        assert len(jpg_files) == 1
        assert len(json_files) == 1

    @patch('shutil.disk_usage')
    @patch('CamController.Publishers.FilePublisher.logger')
    def test_publish_with_low_space_stop_mode(self, mock_logger, mock_disk_usage):
        """Test publish operation with low disk space in stop_saving mode."""
        mock_disk_usage.return_value = (1000*1024*1024, 950*1024*1024, 50*1024*1024)  # Low space
        
        self.test_settings["Cam"]["storage_management"]["mode"] = "stop_saving"
        self.publisher.initialize(self.test_settings)
        
        # Sample image data
        image_data = bytearray([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 100 + [0xFF, 0xD9])
        metadata = {"timestamp": int(time.time())}
        
        self.publisher.publish(image_data, metadata)
        
        # Should not create files
        files = os.listdir(self.temp_dir)
        assert len(files) == 0
        
        # Should log error
        mock_logger.error.assert_called()

    @patch('shutil.disk_usage')
    @patch('CamController.Publishers.FilePublisher.logger')
    def test_publish_with_low_space_delete_mode(self, mock_logger, mock_disk_usage):
        """Test publish operation with low disk space in delete_old mode."""
        mock_disk_usage.side_effect = [
            (1000*1024*1024, 950*1024*1024, 50*1024*1024),  # Low space initially
            (1000*1024*1024, 850*1024*1024, 150*1024*1024), # OK after deletion
            (1000*1024*1024, 850*1024*1024, 150*1024*1024), # Still OK
        ]
        
        self.publisher.initialize(self.test_settings)
        
        # Create old files to be deleted
        file_system = MockFileSystem(self.temp_dir)
        file_system.create_test_files(5)
        initial_count = file_system.get_file_count()
        
        # Sample image data
        image_data = bytearray([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 100 + [0xFF, 0xD9])
        metadata = {"timestamp": int(time.time())}
        
        self.publisher.publish(image_data, metadata)
        
        # Should create new files and delete some old ones
        files = os.listdir(self.temp_dir)
        jpg_files = [f for f in files if f.endswith('.jpg')]
        json_files = [f for f in files if f.endswith('.json')]
        
        assert len(jpg_files) >= 1  # At least the new file
        assert len(json_files) >= 1  # At least the new metadata
        
        final_count = file_system.get_file_count()
        assert final_count <= initial_count + 2  # May have deleted some old files

if __name__ == "__main__":
    pytest.main([__file__])