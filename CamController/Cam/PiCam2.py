# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import Picamera2CamBase
import logging
logger = logging.getLogger("cam.PiCam2")


class PiCam2(Picamera2CamBase.Picamera2CamBase):
    def __init__(self):
        super(PiCam2, self).__init__(
            camera_name="PiCam2",
            image_resolutions=[
                (3280, 2464),
                (1920, 1080),
                (1640, 1232),
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
    