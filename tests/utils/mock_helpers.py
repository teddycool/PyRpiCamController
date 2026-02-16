# Mock utilities for testing
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import os
import time
from unittest.mock import MagicMock, patch
from typing import Tuple, List

class MockDiskUsage:
    """Mock disk usage scenarios for testing."""
    
    def __init__(self, total_mb: int = 1000, free_mb: int = 200):
        self.total_bytes = total_mb * 1024 * 1024
        self.free_bytes = free_mb * 1024 * 1024
        self.used_bytes = self.total_bytes - self.free_bytes
    
    def __call__(self, path: str) -> Tuple[int, int, int]:
        return (self.total_bytes, self.used_bytes, self.free_bytes)
    
    def set_free_space(self, free_mb: int):
        """Update free space for testing different scenarios."""
        self.free_bytes = free_mb * 1024 * 1024
        self.used_bytes = self.total_bytes - self.free_bytes
    
    def set_total_space(self, total_mb: int):
        """Update total space for testing different scenarios."""
        self.total_bytes = total_mb * 1024 * 1024
        self.used_bytes = self.total_bytes - self.free_bytes

class MockFileSystem:
    """Mock file system for testing file operations."""
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.files = {}  # filepath -> (size, mtime)
    
    def create_test_files(self, count: int = 5, base_time: int = None) -> List[str]:
        """Create test image and metadata files."""
        if base_time is None:
            base_time = int(time.time()) - (count * 3600)  # 1 hour apart
        
        created_files = []
        for i in range(count):
            timestamp = base_time + (i * 3600)
            
            # Create image file
            img_path = os.path.join(self.temp_dir, f"{timestamp}.jpg")
            with open(img_path, 'wb') as f:
                f.write(b'fake_image_data' * 100)  # ~1.5KB file
            created_files.append(img_path)
            
            # Create metadata file  
            meta_path = os.path.join(self.temp_dir, f"{timestamp}.json")
            with open(meta_path, 'w') as f:
                f.write('{"timestamp": ' + str(timestamp) + '}')
            created_files.append(meta_path)
            
            # Track files
            self.files[img_path] = (os.path.getsize(img_path), timestamp)
            self.files[meta_path] = (os.path.getsize(meta_path), timestamp)
        
        return created_files
    
    def get_file_count(self) -> int:
        """Get current file count in temp directory."""
        return len([f for f in os.listdir(self.temp_dir) if os.path.isfile(os.path.join(self.temp_dir, f))])
    
    def get_oldest_files(self, count: int = 2) -> List[str]:
        """Get the oldest files for testing deletion."""
        all_files = []
        for filename in os.listdir(self.temp_dir):
            filepath = os.path.join(self.temp_dir, filename)
            if os.path.isfile(filepath):
                mtime = os.path.getmtime(filepath)
                all_files.append((filepath, mtime))
        
        # Sort by modification time and return oldest
        all_files.sort(key=lambda x: x[1])
        return [f[0] for f in all_files[:count]]

def create_mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger

def patch_file_publisher_logger():
    """Patch the FilePublisher logger for testing."""
    return patch('CamController.Publishers.FilePublisher.logger', create_mock_logger())