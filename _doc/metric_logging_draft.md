# Metric logging draft

Branch: `feature/cam-metrics-schema`

## Goal

Make `cam.log` the primary source for performance and thermal analysis by writing one stable structured metric line at a fixed interval, plus a small set of event/snapshot lines at startup and configuration changes.

This draft defines the log format only. No implementation yet.

## Principles

- Human readable first, machine parseable second.
- One schema for all devices and camera types.
- Use a stable `event` name and versioned schema.
- Keep values numeric where possible.
- Include both requested and effective stream settings.
- Preserve backwards compatibility by only adding fields, not renaming existing ones.

## Recommended log strategy

1. Startup summary line
2. Configuration snapshot line on state changes or stream restarts
3. Periodic metric line every 5–10 seconds
4. Event lines for warnings/errors such as thermal throttling or sensor read failures

## Final log line shape

Each metric line should be a single JSON object stored in the existing JSON-formatted `cam.log` message field.

### Outer log envelope

The current file format already wraps log records like this:

```json
{
  "time": "2026-08-23 10:15:00,000",
  "logname": "cam.metrics",
  "logLevel": "INFO",
  "message": "{...metric payload...}"
}
```

### Inner metric payload

The `message` field should contain a compact JSON string with this shape:

```json
{
  "event": "metric",
  "schema_version": 1,
  "source": "mainloop",
  "timestamp": 1755944100.0,
  "software_version": "1.5.8",
  "mode": "Stream",
  "camera": {
    "type": "PiCam3"
  },
  "stream": {
    "requested_resolution": [1920, 1080],
    "effective_resolution": [1920, 1080],
    "requested_fps": 15,
    "effective_fps": 15,
    "encoded_fps": 15,
    "clients": 1
  },
  "temperature": {
    "cpu_c": 88.1,
    "env_c": 42.7,
    "board_c": null,
    "ds18b20_available": true
  },
  "cpu": {
    "load_1m": 1.42,
    "load_5m": 1.18,
    "load_15m": 0.97,
    "throttled": 0
  },
  "memory": {
    "used_mb": 312.4,
    "available_mb": 1684.1
  },
  "storage": {
    "used_percent": 49.8,
    "free_mb": 25788.9
  }
}
```

## Exact field recommendations

### Required top-level fields

- `event`: fixed string, usually `metric`
- `schema_version`: integer, start with `1`
- `source`: one of `startup`, `mainloop`, `stream`, `state`, `publisher`, `ota`, `sensor`
- `timestamp`: Unix epoch float or int
- `software_version`: string read from VERSION file
- `mode`: current high-level operating mode, for example `Cam` or `Stream`

### Camera block

- `camera.type`: camera model or `WebCam`

### Stream block

- `requested_resolution`: configured resolution from settings
- `effective_resolution`: actual active resolution reported by camera backend
- `requested_fps`: configured target fps from settings
- `effective_fps`: actual target fps currently set in backend
- `encoded_fps`: current encoded/output fps if available
- `clients`: active local client count if available

### Temperature block

- `cpu_c`: CPU temperature in Celsius
- `env_c`: environmental temperature in Celsius, if DS18B20 is present
- `board_c`: optional board temp if ever added later
- `ds18b20_available`: boolean

### CPU block

- `load_1m`, `load_5m`, `load_15m`: from `os.getloadavg()`
- `throttled`: integer bitmask from `vcgencmd get_throttled` when available, otherwise `null`

### Memory block

- `used_mb`
- `available_mb`

### Storage block

- `used_percent`
- `free_mb`

## Startup summary line

At service start, emit a single `startup` payload before the first periodic metric line.

Example:

```json
{
  "event": "startup",
  "schema_version": 1,
  "source": "startup",
  "timestamp": 1755944100.0,
  "software_version": "1.5.8",
  "device_id": "10000000a3d1519f",
  "mode": "Stream",
  "camera": {
    "type": "PiCam3"
  },
  "stream": {
    "requested_resolution": [1920, 1080],
    "requested_fps": 15
  },
  "limits": {
    "max_cpu_temp_c": 85.0,
    "cpu_temp_check_s": 10,
    "ds18b20_check_s": 60,
    "metric_interval_s": 10
  }
}
```

## Configuration snapshot line

Emit when stream settings change or when entering StreamState.

Example:

```json
{
  "event": "config_snapshot",
  "schema_version": 1,
  "source": "state",
  "timestamp": 1755944105.0,
  "software_version": "1.5.8",
  "mode": "Stream",
  "camera": {
    "type": "PiCam3"
  },
  "stream": {
    "requested_resolution": [2304, 1296],
    "effective_resolution": [2304, 1296],
    "requested_fps": 25,
    "effective_fps": 25
  }
}
```

## Thermal event line

Keep the human-readable error line, but add a structured payload that analysis tooling can parse.

Example:

```json
{
  "event": "thermal_overheat",
  "schema_version": 1,
  "source": "mainloop",
  "timestamp": 1755944106.0,
  "software_version": "1.5.8",
  "cpu": {
    "temperature_c": 88.6,
    "load_1m": 1.42,
    "load_5m": 1.18,
    "load_15m": 0.97,
    "throttled": 0
  },
  "action": {
    "type": "cool_off",
    "duration_s": 300
  }
}
```

## Suggested log levels

- `INFO` for startup, configuration snapshots, and regular metric lines
- `WARNING` for recoverable sensor read failures or degraded conditions
- `ERROR` for overheat, shutdown, or unrecoverable sensor failures

## Why this shape works

- A single `cam.log` file becomes enough for time-series comparison.
- `startup` and `config_snapshot` provide anchors for before/after update analysis.
- `metric` lines give continuous numeric data for graphs.
- `schema_version` lets the format evolve safely.
- `source` keeps metric producers identifiable without changing field names.

## Open follow-up items

- Decide whether `metric_interval_s` should be configurable.
- Decide whether `encoded_fps` should be reported from the camera backend or from measured output.
- Decide whether memory and storage should be included in every metric line or only on startup plus periodic summaries.
- Decide whether the web GUI should overlay update timestamps on charts.
