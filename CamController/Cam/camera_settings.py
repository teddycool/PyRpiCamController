# This software-file was created by Par Sundback and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

from dataclasses import dataclass
from typing import Any


Resolution = tuple[int, int]


@dataclass(frozen=True)
class CameraSettings:
    resolution: Resolution
    brightness: float | None = None

    @classmethod
    def from_settings(cls, settings: dict[str, Any], default_resolution: Resolution) -> "CameraSettings":
        cam_settings = settings.get("Cam", {})
        resolution = tuple(cam_settings.get("resolution", default_resolution))
        brightness = cam_settings.get("brightness")
        return cls(resolution=resolution, brightness=brightness)


@dataclass(frozen=True)
class StreamSettings:
    resolution: Resolution
    framerate: int

    @classmethod
    def from_settings(
        cls,
        settings: dict[str, Any],
        default_resolution: Resolution,
        default_framerate: int = 20,
    ) -> "StreamSettings":
        stream_settings = settings.get("Stream", {})
        resolution = tuple(stream_settings.get("resolution", default_resolution))
        framerate = int(stream_settings.get("framerate", default_framerate))
        return cls(resolution=resolution, framerate=framerate)
