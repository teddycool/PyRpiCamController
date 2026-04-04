# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Parent-class for all cams
#https://en.wikipedia.org/wiki/State_pattern
from typing import Any


Resolution = tuple[int, int]


class CamBase:

    def __init__(self) -> None:
        self._current_image: Any = None  # Must be a numpy array
        self._current_metadata: dict[str, Any] | None = None
        self._supported_image_resolutions: list[Resolution] = []
        self._supported_video_resolutions: list[Resolution] = []

    def initialize(self, settings: dict[str, Any]) -> None:  # Init camera with current settings from config
        raise NotImplementedError

    def update(self, context: Any = None) -> None:  # Update current image (and metadata) with latest frame from cam
        raise NotImplementedError 

    def is_image_resolution_supported(self, res: Resolution) -> bool:  # Check if res (x,y) is supported by camera for images
        return self._supported_image_resolutions.count(res) == 1
    
    def is_video_resolution_supported(self, res: Resolution) -> bool:  # Check if res (x,y) is supported by camera for video
        return self._supported_video_resolutions.count(res) == 1

    def start_stream(self, settings: dict[str, Any] | None = None) -> None:  # Start streaming to io-buffer
        raise NotImplementedError




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