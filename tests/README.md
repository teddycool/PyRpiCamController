# Test README for PyRpiCamController Storage Management Tests
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

## Overview

This test suite provides comprehensive testing for the disk space management feature in PyRpiCamController. The tests are designed to run on development machines without requiring the actual Raspberry Pi hardware.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py             # Pytest fixtures and configuration
├── requirements.txt        # Test dependencies
├── pytest.ini             # Pytest configuration
├── run_tests.py           # Test runner script
├── README.md              # This file
├── fixtures/              # Test data and schemas
│   └── test_settings_schema.json
├── utils/                 # Test utilities and mocks
│   ├── __init__.py
│   └── mock_helpers.py    # Mock classes for testing
├── unit/                  # Unit tests
│   ├── __init__.py
│   ├── test_file_publisher.py     # FilePublisher tests
│   ├── test_settings_manager.py   # SettingsManager tests
│   └── test_edge_cases.py         # Edge case tests
└── integration/           # Integration tests
    ├── __init__.py
    └── test_storage_system.py     # End-to-end tests
```

## Installation

1. Install test dependencies:
```bash
cd /path/to/PyRpiCamController
pip install -r tests/requirements.txt
```

2. Verify installation:
```bash
python tests/run_tests.py --check-requirements
```

## Running Tests

### Quick Start
```bash
# Run all tests with coverage
python tests/run_tests.py

# Run only unit tests
python tests/run_tests.py --type unit

# Run only integration tests  
python tests/run_tests.py --type integration

# Run tests without coverage reporting
python tests/run_tests.py --no-coverage

# Run tests with verbose output
python tests/run_tests.py --verbose
```

### Using pytest directly
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_file_publisher.py

# Run specific test method
pytest tests/unit/test_file_publisher.py::TestFilePublisherDiskManagement::test_is_disk_space_low_mb_threshold

# Run with coverage
pytest tests/ --cov=CamController --cov=Settings --cov-report=html
```

## Test Categories

### Unit Tests (`tests/unit/`)

**test_file_publisher.py**
- Disk space detection (MB and percentage thresholds)
- File deletion logic
- Storage management modes (stop_saving vs delete_old)
- Settings initialization
- Error handling

**test_settings_manager.py**
- Storage management settings loading/saving
- Settings validation
- User settings override defaults
- Enum validation (storage modes, threshold units)

**test_edge_cases.py**
- Permission errors during file operations
- Corrupted metadata files
- Disk full scenarios
- Boundary value testing
- Invalid configurations

### Integration Tests (`tests/integration/`)

**test_storage_system.py**
- End-to-end workflow: Settings → FilePublisher → Storage management
- Settings persistence across restarts
- Different threshold behaviors
- Mode switching effects
- Disabled storage management

## Test Features

### Mocking System Components
- **MockDiskUsage**: Simulates different disk space scenarios
- **MockFileSystem**: Creates temporary test files with controlled timestamps
- **Mock loggers**: Capture and verify log output

### Temporary File Management
- All tests use temporary directories
- Automatic cleanup after each test
- No interference between test runs

### Coverage Reporting
- Line coverage for all modules
- Branch coverage for conditional logic
- HTML reports generated in `tests/reports/coverage_html/`
- Terminal coverage summary

## Key Test Scenarios

1. **Normal Operation**: Sufficient disk space, files saved normally
2. **Low Space + Delete Mode**: Old files deleted to make space
3. **Low Space + Stop Mode**: New files rejected when space is low
4. **Settings Changes**: Dynamic behavior changes based on configuration
5. **Edge Cases**: Permission errors, corrupted files, extreme values
6. **Persistence**: Settings survive application restarts

## Mock vs Real Components

### What's Mocked
- `shutil.disk_usage()`: Disk space information
- File system operations when testing error conditions
- Logging output for verification

### What's Real
- Settings loading/saving logic
- File creation/deletion operations
- JSON parsing and validation
- Directory traversal and file sorting

## Development Workflow

### Adding New Tests
1. Create test file in appropriate directory (`unit/` or `integration/`)
2. Use existing fixtures from `conftest.py`
3. Follow naming convention: `test_*.py` files, `Test*` classes, `test_*` methods
4. Add mocks only when necessary for isolation

### Test Data
- Use `MockFileSystem` for creating test files
- Use fixtures from `conftest.py` for common test data
- Store complex test schemas in `fixtures/` directory

### Running During Development
```bash
# Run tests on file save (requires pytest-watch)
ptw tests/

# Run specific test during development
pytest tests/unit/test_file_publisher.py::TestFilePublisherDiskManagement::test_publish_with_sufficient_space -v -s
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure project paths are correct
export PYTHONPATH=/path/to/PyRpiCamController:$PYTHONPATH
```

**Missing Dependencies**
```bash
pip install -r tests/requirements.txt
```

**Permission Errors in Tests**
- Tests use temporary directories, should not require special permissions
- If seeing permission errors, check that `/tmp` is writable

**Coverage Not Working**
- Ensure `pytest-cov` is installed
- Check that module paths in coverage config match your project structure

### Debug Options
```bash
# Run with debug output
pytest tests/ -v -s --tb=long

# Run single test with debugging
pytest tests/unit/test_file_publisher.py::test_specific_method -v -s --pdb
```

## Continuous Integration

The test suite is designed to work in CI environments:

```yaml
# Example GitHub Actions configuration
- name: Run tests
  run: |
    pip install -r tests/requirements.txt
    python tests/run_tests.py --no-coverage
```

## Performance

- Unit tests: ~5-10 seconds
- Integration tests: ~10-20 seconds  
- Complete suite: ~30 seconds
- Coverage analysis adds ~5 seconds

Tests are designed to be fast and reliable for frequent execution during development.