# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import Picamera2CamBase
import logging
logger = logging.getLogger("cam.PiCamHQ")


class PiCamHQ(Picamera2CamBase.Picamera2CamBase):
    def __init__(self):
        super().__init__(
            camera_name="PiCamHQ",
            image_resolutions=[
                (4056, 3040),
                (2028, 1520),
                (1920, 1080),
                (1332, 990),
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

    def _resolve_image_resolution(self, settings):
        cam_settings = settings.get("Cam", {})
        requested_res = cam_settings.get("resolution")

        if requested_res is None and "width" in cam_settings and "height" in cam_settings:
            requested_res = (cam_settings["width"], cam_settings["height"])

        if requested_res is None:
            requested_res = self._supported_image_resolutions[0]

        requested_res = tuple(requested_res)

        if requested_res not in self._supported_image_resolutions:
            self._logger.warning("Cam resolution %s requested in config, but not supported by PiCamHQ", str(requested_res))
            self._logger.info("Using fallback image resolution %s", str(self._supported_image_resolutions[0]))
            return self._supported_image_resolutions[0]
        return requested_res
    