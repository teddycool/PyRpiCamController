# PyRpiCamController Integration Tests

Comprehensive system-level integration tests for PyRpiCamController running on Raspberry Pi hardware.

## Overview

This test framework validates the complete PyRpiCamController system by:
- Changing settings via the web API
- Triggering camera operations
- Verifying actual behavior matches expected results
- Testing on real Raspberry Pi hardware

## Quick Start

### Prerequisites

1. Raspberry Pi with PyRpiCamController installed and running
2. Network connectivity to the Pi
3. Python 3.7+ on test runner machine

### Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Configure test target
cd config/
cp test_config.yaml test_config.yaml.local
# Edit test_config.yaml.local with your Pi's hostname/IP
```

### Running Tests

```bash
# Run all tests
pytest tests/integration/

# Run with custom target
pytest tests/integration/ --target raspberrypi.local

# Run specific test suite
pytest tests/integration/test_suites/test_camera_settings.py

# Run with verbose output
pytest tests/integration/ -v

# Run only smoke tests
pytest tests/integration/ -m smoke

# Generate HTML report
pytest tests/integration/ --html=reports/test_report.html

# Keep test images for inspection
pytest tests/integration/ --keep-images

# Skip cleanup (for debugging)
pytest tests/integration/ --skip-cleanup
```

## Test Structure

```
tests/integration/
├── api_client/          # API wrapper classes
│   ├── web_api.py       # Web GUI API client
│   ├── stream_api.py    # Streaming server API client
│   └── system_api.py    # System-level operations
├── validators/          # Result validation
│   ├── image_validator.py
│   └── timing_validator.py
├── utils/               # Helper utilities
│   ├── wait_helpers.py
│   ├── cleanup.py
│   └── config_loader.py
├── test_suites/         # Test modules
│   └── test_camera_settings.py
├── config/              # Configuration files
│   └── test_config.yaml
└── conftest.py          # Pytest fixtures
```

## Test Categories

### Camera Settings Tests
- **Resolution Tests**: Validate image dimensions match configured resolution
- **Timeslot Tests**: Verify capture intervals are accurate
- **Publisher Tests**: Test file and URL publishing functionality
- **Mode Switching**: Test transitions between Cam and Stream modes

### Validators

#### ImageValidator
```python
# Validate image resolution
assert image_validator.validate_resolution(
    image_path, 
    expected_width=1920, 
    expected_height=1080
)

# Validate file format
assert image_validator.validate_format(image_path, "JPEG")

# Validate metadata exists
assert image_validator.validate_metadata(json_path)
```

#### TimingValidator
```python
# Validate capture intervals
assert timing_validator.validate_capture_interval(
    timestamps,
    expected_interval=5.0,
    tolerance=2.0
)
```

## Configuration

Edit `config/test_config.yaml`:

```yaml
target:
  host: "raspberrypi.local"  # Your Pi's hostname or IP
  web_port: 80
  stream_port: 8081
  image_directory: "/home/pi/shared/images/"

timeouts:
  service_restart: 30
  first_image: 60
  
test_settings:
  cleanup_after_test: true
  restore_original_settings: true
```

## Writing New Tests

### Basic Test Pattern

```python
def test_example_setting(web_api, system_api, restore_settings, config):
    """Test description"""
    
    # 1. Save original settings
    restore_settings(['Cam.some_setting'])
    
    # 2. Change setting
    web_api.set_setting('Cam.some_setting', new_value)
    
    # 3. Apply and restart
    web_api.apply_and_restart()
    web_api.wait_for_service_ready()
    
    # 4. Wait for behavior
    time.sleep(config.first_image_timeout)
    
    # 5. Validate result
    result = system_api.check_something()
    assert result == expected
    
    # Settings automatically restored by restore_settings fixture
```

### Using Fixtures

Available pytest fixtures:
- `config`: Test configuration
- `web_api`: Web API client
- `system_api`: System API client  
- `stream_api`: Stream API client
- `image_validator`: Image validation
- `timing_validator`: Timing validation
- `restore_settings`: Auto-restore settings after test
- `cleanup_handler`: Cleanup management

## API Clients

### WebAPIClient

```python
# Get setting
value = web_api.get_setting('Cam.resolution')

# Set setting
web_api.set_setting('Cam.resolution', [1920, 1080])

# Apply changes and restart
web_api.apply_and_restart()
web_api.wait_for_service_ready()

# Get stream status
status = web_api.get_stream_status()
```

### SystemAPI

```python
# Check service status
is_running = system_api.check_service_status('camcontroller.service')

# Count images
count = system_api.count_images_in_directory('/home/pi/shared/images/')

# Get latest image
filepath, timestamp = system_api.get_latest_image('/home/pi/shared/images/')

# Read logs
lines = system_api.read_log_tail('/home/pi/shared/logs/cam.log', 50)
```

### StreamAPIClient

```python
# Get stream info
info = stream_api.get_stream_info()

# Check if streaming
is_streaming = stream_api.is_streaming()

# Measure actual FPS
fps = stream_api.measure_actual_fps(duration=5)
```

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.smoke  # Quick connectivity/smoke tests
@pytest.mark.slow   # Long-running tests
@pytest.mark.hardware  # Requires specific hardware
```

Run specific markers:
```bash
pytest -m smoke  # Run only smoke tests
pytest -m "not slow"  # Skip slow tests
```

## Troubleshooting

### Cannot connect to Pi
- Verify Pi is reachable: `ping raspberrypi.local`
- Check web interface is running: `http://raspberrypi.local` in browser
- Verify firewall settings on Pi

### Tests timeout
- Increase timeouts in `config/test_config.yaml`
- Check Pi system load and CPU temperature
- Verify camera is functioning

### Settings not applying
- Check `/home/pi/shared/logs/cam.log` on Pi for errors
- Verify service is running: `systemctl status camcontroller.service`
- Check disk space on Pi

## Best Practices

1. **Always use restore_settings fixture** to prevent test interactions
2. **Add appropriate timeouts** for asynchronous operations
3. **Log extensively** for debugging failed tests
4. **Validate assumptions** (service running, disk space, etc.)
5. **Use parametrize** for testing multiple similar cases
6. **Keep tests independent** - don't rely on test execution order

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r tests/integration/requirements-test.txt
      - run: pytest tests/integration/ --target ${{ secrets.TEST_PI_HOST }}
```

## Contributing

When adding new tests:
1. Follow existing patterns and conventions
2. Add docstrings explaining what is tested
3. Use appropriate fixtures
4. Add parametrization for similar test cases
5. Update this README with new test capabilities

## License

Same as PyRpiCamController - GNU GPLv3
