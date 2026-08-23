# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

from __future__ import annotations

from typing import Any, Tuple
import logging

from picamera2 import Picamera2


def resolve_camera_interface(settings: dict[str, Any], logger: logging.Logger, camera_name: str) -> int:
    """Resolve Picamera2 camera index from runtime settings.

    Expected source: top-level hwconfig key CamInterface.
    """
    raw = settings.get("CamInterface", 0)
    if isinstance(raw, dict):
        raw = raw.get("value", 0)

    try:
        index = int(raw)
    except (TypeError, ValueError):
        logger.warning("%s invalid CamInterface '%s'; defaulting to 0", camera_name, raw)
        return 0

    if index < 0:
        logger.warning("%s CamInterface %s is < 0; defaulting to 0", camera_name, index)
        return 0

    return index


def create_picamera2(settings: dict[str, Any], logger: logging.Logger, camera_name: str) -> Tuple[Picamera2, int]:
    """Create Picamera2 instance for configured interface with robust fallback."""
    camera_index = resolve_camera_interface(settings, logger, camera_name)

    try:
        return Picamera2(camera_num=camera_index), camera_index
    except TypeError:
        return Picamera2(), camera_index
    except Exception as ex:
        if camera_index != 0:
            logger.warning(
                "%s failed opening camera interface %s (%s). Falling back to interface 0.",
                camera_name,
                camera_index,
                ex,
            )
            try:
                return Picamera2(camera_num=0), 0
            except TypeError:
                return Picamera2(), 0
        raise
