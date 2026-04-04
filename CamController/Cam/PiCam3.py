# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import Picamera2CamBase
import libcamera
import logging
logger = logging.getLogger("cam.PiCam3")


class PiCam3(Picamera2CamBase.Picamera2CamBase):
    def __init__(self):
        super().__init__(
            camera_name="PiCam3",
            image_resolutions=[
                (4608, 2592),
                (2304, 1296),
                (1920, 1080),
                (1536, 864),
                (1280, 720),
                (640, 480),
            ],
            video_resolutions=[
                (1920, 1080),
                (1280, 720),
                (640, 480),
            ],
        )
        self._logger = logger

    def _get_camera_specific_controls(self, settings):
        return {
            "AfMode": libcamera.controls.AfModeEnum.Continuous,
        }
    