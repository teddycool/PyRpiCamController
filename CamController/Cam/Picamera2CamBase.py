# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import CamBase
from picamera2 import Picamera2
import libcamera


class Picamera2CamBase(CamBase.CamBase):
    def __init__(self, camera_name, image_resolutions, video_resolutions):
        super(Picamera2CamBase, self).__init__()
        self._camera_name = camera_name
        self._supportedImagesResolutions = image_resolutions
        self._supportedVideoResolutions = video_resolutions
        self._cam = None
        self._camconf = None

    def _resolve_image_resolution(self, settings):
        requested_res = settings.get("Cam", {}).get("resolution", self._supportedImagesResolutions[0])
        requested_res = tuple(requested_res)

        if requested_res not in self._supportedImagesResolutions:
            self._logger.warning(
                "Cam resolution %s requested in config, but not supported by %s",
                str(requested_res),
                self._camera_name,
            )
            self._logger.info("Using fallback image resolution %s", str(self._supportedImagesResolutions[0]))
            return self._supportedImagesResolutions[0]

        return requested_res

    def _resolve_stream_resolution(self, settings):
        requested_res = settings.get("Stream", {}).get("resolution", self._supportedVideoResolutions[0])
        requested_res = tuple(requested_res)

        if requested_res not in self._supportedVideoResolutions:
            self._logger.warning(
                "Stream resolution %s requested in config, but not supported by %s",
                str(requested_res),
                self._camera_name,
            )
            self._logger.info("Using fallback stream resolution %s", str(self._supportedVideoResolutions[0]))
            return self._supportedVideoResolutions[0]

        return requested_res

    def _get_common_controls(self, settings):
        controls = {
            "AwbMode": libcamera.controls.AwbModeEnum.Auto,
            "AeEnable": True,
            "AwbEnable": True,
        }

        if "brightness" in settings.get("Cam", {}):
            controls["Brightness"] = settings["Cam"]["brightness"]

        return controls

    def _get_camera_specific_controls(self, settings):
        return {}

    def _get_stream_controls(self, settings):
        return {
            "FrameRate": settings.get("Stream", {}).get("framerate", 20),
        }

    def _apply_runtime_controls(self, settings):
        controls = self._get_common_controls(settings)
        controls.update(self._get_camera_specific_controls(settings))
        self._cam.set_controls(controls)

    def start(self, settings):
        res = self._resolve_image_resolution(settings)
        self._cam = Picamera2()
        self._camconf = self._cam.create_still_configuration(
            main={"format": "RGB888", "size": res}
        )
        self._logger.info("%s still config: %s", self._camera_name, str(self._camconf.get("main")))
        self._cam.configure(self._camconf)
        self._cam.start(show_preview=False)
        self._apply_runtime_controls(settings)

    def initialize(self, settings):
        if self._cam is not None:
            self._apply_runtime_controls(settings)

    def update(self):
        try:
            request = self._cam.capture_request()
            self._currentMetaData = request.get_metadata()
            self._currentimg = request.make_array("main")
            request.release()

            self._logger.debug("Current image size: %s", str(self._currentimg.size))
            self._logger.debug("Current image buffer updated")
        except Exception:
            self._logger.warning("Failed to update image buffer", exc_info=True)
            self._currentimg = None
            self._currentMetaData = None

    def start_stream(self, settings=None):
        if settings is None:
            settings = {}
        stream_res = self._resolve_stream_resolution(settings)
        self._cam = Picamera2()
        self._camconf = self._cam.create_video_configuration(
            main={"format": "RGB888", "size": stream_res},
            controls=self._get_stream_controls(settings),
        )
        self._logger.info("%s stream config: %s", self._camera_name, str(self._camconf.get("main")))
        self._cam.configure(self._camconf)
        self._cam.start(show_preview=False)
        self._apply_runtime_controls(settings)

    def stop(self):
        if self._cam is not None:
            self._cam.stop()
            self._cam.close()
            self._cam = None

    def __del__(self):
        self.stop()
