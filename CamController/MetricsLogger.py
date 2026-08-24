# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import json
import logging
import math
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


METRICS_SCHEMA = "cam-metrics-v1"
DEFAULT_METRICS_LOG_PATH = "/home/pi/shared/logs/cam-metrics.log"
DEFAULT_METRICS_LOG_SIZE = 1_000_000
DEFAULT_METRICS_LOG_BACKUPS = 5
RETENTION_WINDOW_SECONDS = 24 * 60 * 60
MIN_INTERVAL_SECONDS = 5
DEFAULT_ESTIMATED_EVENT_BYTES = 900
RETENTION_UTILIZATION_FACTOR = 0.85
MAX_AUTO_BACKUP_COUNT = 200


class MetricsJsonFormatter(logging.Formatter):
    def format(self, record):
        payload = record.msg if isinstance(record.msg, dict) else {"message": record.getMessage()}
        if not isinstance(payload, dict):
            payload = {"message": str(payload)}

        event = {
            "schema": METRICS_SCHEMA,
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
        }
        event.update(payload)
        return json.dumps(event, separators=(",", ":"), ensure_ascii=False)


def calculate_min_backup_count_for_24h(
    max_bytes: int,
    interval_seconds: float,
    estimated_event_bytes: int = DEFAULT_ESTIMATED_EVENT_BYTES,
) -> int:
    """Return minimum backupCount required to keep ~24h of metrics history."""
    safe_max_bytes = max(10_000, int(max_bytes))
    safe_interval = max(float(interval_seconds), float(MIN_INTERVAL_SECONDS))
    safe_event_bytes = max(200, int(estimated_event_bytes))

    expected_events = max(1, int(math.ceil(RETENTION_WINDOW_SECONDS / safe_interval)))
    required_total_bytes = int(math.ceil((expected_events * safe_event_bytes) / RETENTION_UTILIZATION_FACTOR))
    required_files = max(1, int(math.ceil(required_total_bytes / safe_max_bytes)))

    return max(1, required_files - 1)


def setup_metrics_logger(settings: Any) -> logging.Logger:
    """Configure the dedicated structured metrics logger."""
    logger = logging.getLogger("cam.metrics")
    if getattr(logger, "_metrics_configured", False):
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not bool(settings.get("MetricsLogToFile", True)):
        logger.addHandler(logging.NullHandler())
        logger._metrics_configured = True
        return logger

    log_path = Path(str(settings.get("MetricsLogFilePath", DEFAULT_METRICS_LOG_PATH)))
    max_bytes = int(settings.get("MetricsLogFileSize", DEFAULT_METRICS_LOG_SIZE))
    configured_backup_count = int(settings.get("MetricsLogBackupCount", DEFAULT_METRICS_LOG_BACKUPS))
    interval_seconds = float(settings.get("MetricsInterval", 30))

    required_backup_count = calculate_min_backup_count_for_24h(
        max_bytes=max_bytes,
        interval_seconds=interval_seconds,
    )
    effective_backup_count = max(configured_backup_count, required_backup_count)
    effective_backup_count = min(effective_backup_count, MAX_AUTO_BACKUP_COUNT)

    if effective_backup_count > configured_backup_count:
        logging.getLogger(__name__).warning(
            "Metrics rotation backup count raised from %s to %s to retain ~24h history "
            "(size=%s bytes, interval=%ss)",
            configured_backup_count,
            effective_backup_count,
            max_bytes,
            interval_seconds,
        )

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=effective_backup_count)
    except Exception:
        fallback_path = Path("/tmp/cam-metrics.log")
        handler = RotatingFileHandler(fallback_path, maxBytes=max_bytes, backupCount=effective_backup_count)

    handler.setFormatter(MetricsJsonFormatter())
    logger.addHandler(handler)
    logger._metrics_configured = True
    return logger


def emit_metrics(event: str, data: dict[str, Any] | None = None, **fields: Any) -> None:
    """Emit one structured metrics event to the dedicated metrics logger."""
    logger = logging.getLogger("cam.metrics")
    payload: dict[str, Any] = {"event": event}

    if data is not None:
        payload["data"] = data

    if fields:
        payload.update(fields)

    logger.info(payload)