# Pytest configuration and shared fixtures
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import pytest
import tempfile
import os
import shutil
import json
from unittest.mock import MagicMock, patch
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'CamController'))
sys.path.insert(0, os.path.join(project_root, 'Settings'))

@pytest.fixture
def temp_image_dir():
    """Create a temporary directory for image storage during tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_image_data():
    """Create sample image data for testing."""
    # Create a simple fake JPEG data
    return bytearray([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 100 + [0xFF, 0xD9])

@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return {
        "timestamp": 1640995200,
        "camera_settings": {
            "resolution": "1920x1080",
            "exposure": "auto"
        },
        "device_info": {
            "device_id": "test_device",
            "location": "test_location"
        }
    }

@pytest.fixture
def default_settings():
    """Create default settings for testing."""
    return {
        "Cam": {
            "publishers": {
                "file": {
                    "publish": True,
                    "location": "/tmp/test_images",
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

@pytest.fixture
def mock_disk_usage():
    """Mock shutil.disk_usage for controlled testing."""
    with patch('shutil.disk_usage') as mock:
        # Default: 1GB total, 800MB used, 200MB free
        mock.return_value = (1024*1024*1024, 800*1024*1024, 200*1024*1024)
        yield mock

@pytest.fixture
def settings_schema_fixture():
    """Load test settings schema."""
    schema_path = os.path.join(project_root, 'tests', 'fixtures', 'test_settings_schema.json')
    if os.path.exists(schema_path):
        with open(schema_path, 'r') as f:
            return json.load(f)
    return None