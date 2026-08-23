# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


METRICS_SCHEMA = "cam-metrics-v1"
DEFAULT_METRICS_LOG_PATH = "/home/pi/shared/logs/cam-metrics.log"
DEFAULT_METRICS_LOG_SIZE = 1_000_000
DEFAULT_METRICS_LOG_BACKUPS = 5


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
    backup_count = int(settings.get("MetricsLogBackupCount", DEFAULT_METRICS_LOG_BACKUPS))

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
    except Exception:
        fallback_path = Path("/tmp/cam-metrics.log")
        handler = RotatingFileHandler(fallback_path, maxBytes=max_bytes, backupCount=backup_count)

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