# Integration Tests

Integration tests validate end-to-end behavior of PyRpiCamController on Raspberry Pi hardware.

## Scope

- Change settings through the web API
- Trigger camera operations
- Validate resulting behavior
- Verify stream/system/service interactions

## Prerequisites

1. Raspberry Pi with the project installed and running
2. Network connectivity to the Pi
3. Python 3.7+ on the test runner machine

## Setup

```bash
pip install -r tests/integration/requirements-test.txt
cd tests/integration/config
cp test_config.yaml test_config.yaml.local
```

Edit `test_config.yaml.local` for your target host.

## Running Tests

```bash
pytest tests/integration/
pytest tests/integration/ -v
pytest tests/integration/ -m smoke
pytest tests/integration/test_suites/test_camera_settings.py
```

## Structure

```text
tests/integration/
├── api_client/
├── validators/
├── utils/
├── test_suites/
├── config/
└── conftest.py
```

## Typical Test Pattern

```python
def test_example_setting(web_api, restore_settings):
    restore_settings(["Cam.some_setting"])
    web_api.set_setting("Cam.some_setting", 123)
    web_api.apply_and_restart()
    web_api.wait_for_service_ready()
    assert True
```

## Common Fixtures

- `config`
- `web_api`
- `system_api`
- `stream_api`
- `image_validator`
- `timing_validator`
- `restore_settings`

## Troubleshooting

### Cannot Connect to Pi

- Verify host resolves and is reachable (`ping`)
- Verify web UI responds in browser
- Verify service state on target Pi

### Tests Timeout

- Increase timeouts in test config
- Check target Pi CPU load and temperature
- Check camera availability/logs

### Settings Not Applying

- Check `camcontroller.service` logs
- Confirm apply/restart completed
- Confirm persisted values in `Settings/user_settings.json`

## CI Example

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
      - run: pytest tests/integration/
```

## License

Same as project root: GNU GPLv3.
