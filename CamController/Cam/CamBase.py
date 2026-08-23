# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Parent-class for all cams
#https://en.wikipedia.org/wiki/State_pattern
from abc import ABC, abstractmethod
from typing import Any


Resolution = tuple[int, int]


class CamBase(ABC):

    def __init__(self) -> None:
        self._current_image: Any = None  # Must be a numpy array
        self._current_metadata: dict[str, Any] | None = None
        self._supported_image_resolutions: list[Resolution] = []
        self._supported_video_resolutions: list[Resolution] = []
        self._last_started_at: float | None = None
        self._last_update_at: float | None = None
        self._last_error: str | None = None
        self._current_mode: str | None = None
        self._current_image_resolution: Resolution | None = None
        self._current_stream_resolution: Resolution | None = None
        self._current_stream_framerate: int | None = None
        self._current_stream_bitrate: int | None = None
        self._capture_count: int = 0
        self._stream_capture_count: int = 0

    @property
    def current_image(self) -> Any:
        return self._current_image

    @property
    def current_metadata(self) -> dict[str, Any] | None:
        return self._current_metadata

    @property
    def supported_image_resolutions(self) -> list[Resolution]:
        return list(self._supported_image_resolutions)

    @property
    def supported_video_resolutions(self) -> list[Resolution]:
        return list(self._supported_video_resolutions)

    @abstractmethod
    def initialize(self, settings: dict[str, Any]) -> None:  # Init camera with current settings from config
        raise NotImplementedError

    @abstractmethod
    def start(self, settings: dict[str, Any]) -> None:  # Start camera in capture mode
        raise NotImplementedError

    @abstractmethod
    def update(self, context: Any = None) -> None:  # Update current image (and metadata) with latest frame from cam
        raise NotImplementedError 

    def is_image_resolution_supported(self, res: Resolution) -> bool:  # Check if res (x,y) is supported by camera for images
        return self._supported_image_resolutions.count(res) == 1
    
    def is_video_resolution_supported(self, res: Resolution) -> bool:  # Check if res (x,y) is supported by camera for video
        return self._supported_video_resolutions.count(res) == 1

    @abstractmethod
    def start_stream(self, settings: dict[str, Any] | None = None) -> None:  # Start streaming to io-buffer
        raise NotImplementedError

    @abstractmethod
    def capture_stream_frame(self) -> Any:  # Capture one frame for streaming path
        raise NotImplementedError

    def start_stream_encoded(self, _settings: dict[str, Any], _output: Any) -> bool:
        """Optional fast path: camera handles encoded stream output directly.

        Return True when encoded streaming started successfully, otherwise False
        so callers can use frame-capture fallback.
        """
        return False

    def set_stream_framerate(self, _framerate: int) -> bool:
        """Optional runtime framerate update for encoded streaming paths."""
        return False

    @abstractmethod
    def stop(self) -> None:  # Stop camera and release resources
        raise NotImplementedError

    def cleanup(self) -> None:
        self.stop()

    def dispose(self) -> None:
        self.stop()

    def get_metrics(self) -> dict[str, Any]:
        """Return common camera metrics for the active backend instance."""
        metadata_keys = None
        if isinstance(self._current_metadata, dict):
            metadata_keys = sorted(self._current_metadata.keys())

        image_shape = None
        if self._current_image is not None and hasattr(self._current_image, "shape"):
            try:
                image_shape = list(self._current_image.shape)
            except (AttributeError, TypeError, ValueError):
                image_shape = None

        return {
            "camera": {
                "type": type(self).__name__,
                "camera_name": type(self).__name__,
                "mode": self._current_mode,
                "started_at": self._last_started_at,
                "last_update_at": self._last_update_at,
                "last_error": self._last_error,
                "current_image_present": self._current_image is not None,
                "current_image_shape": image_shape,
                "current_metadata_keys": metadata_keys,
                "image_resolution": list(self._current_image_resolution) if self._current_image_resolution else None,
                "stream_resolution": list(self._current_stream_resolution) if self._current_stream_resolution else None,
                "stream_framerate": self._current_stream_framerate,
                "stream_bitrate": self._current_stream_bitrate,
                "capture_count": self._capture_count,
                "stream_capture_count": self._stream_capture_count,
                "backend_specific": {},
            }
        }


def get_cam(camtype: str) -> CamBase:
    if (camtype == "PiCam2"):
        from Cam import PiCam2
        return PiCam2.PiCam2()
    if (camtype == "PiCam3"):
        from Cam import  PiCam3
        cam = PiCam3.PiCam3()
        return cam
    if (camtype == "PiCamHQ"):
        from Cam import PiCamHQ
        return PiCamHQ.PiCamHQ()
    if (camtype == "WebCam"):
        from Cam import WebCam
        return WebCam.WebCam()
    
    raise ValueError("Unknown camera type: " + str(camtype))