# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import CamBase
from picamera2 import Picamera2
import libcamera
import logging
from typing import Any


class Picamera2CamBase(CamBase.CamBase):
    def __init__(
        self,
        camera_name: str,
        image_resolutions: list[CamBase.Resolution],
        video_resolutions: list[CamBase.Resolution],
    ) -> None:
        super().__init__()
        self._camera_name = camera_name
        self._supported_image_resolutions = image_resolutions
        self._supported_video_resolutions = video_resolutions
        self._cam = None
        self._camera_config = None
        self._logger = logging.getLogger(f"cam.{camera_name}")

    def _resolve_image_resolution(self, settings: dict[str, Any]) -> CamBase.Resolution:
        requested_res = settings.get("Cam", {}).get("resolution", self._supported_image_resolutions[0])
        requested_res = tuple(requested_res)

        if requested_res not in self._supported_image_resolutions:
            self._logger.warning(
                "Cam resolution %s requested in config, but not supported by %s",
                str(requested_res),
                self._camera_name,
            )
            self._logger.info("Using fallback image resolution %s", str(self._supported_image_resolutions[0]))
            return self._supported_image_resolutions[0]

        return requested_res

    def _resolve_stream_resolution(self, settings: dict[str, Any]) -> CamBase.Resolution:
        requested_res = settings.get("Stream", {}).get("resolution", self._supported_video_resolutions[0])
        requested_res = tuple(requested_res)

        if requested_res not in self._supported_video_resolutions:
            self._logger.warning(
                "Stream resolution %s requested in config, but not supported by %s",
                str(requested_res),
                self._camera_name,
            )
            self._logger.info("Using fallback stream resolution %s", str(self._supported_video_resolutions[0]))
            return self._supported_video_resolutions[0]

        return requested_res

    def _get_common_controls(self, settings: dict[str, Any]) -> dict[str, Any]:
        controls = {
            "AwbMode": libcamera.controls.AwbModeEnum.Auto,
            "AeEnable": True,
            "AwbEnable": True,
        }

        if "brightness" in settings.get("Cam", {}):
            controls["Brightness"] = settings["Cam"]["brightness"]

        return controls

    def _get_camera_specific_controls(self, settings: dict[str, Any]) -> dict[str, Any]:
        return {}

    def _get_stream_controls(self, settings: dict[str, Any]) -> dict[str, Any]:
        return {
            "FrameRate": settings.get("Stream", {}).get("framerate", 20),
        }

    def _apply_runtime_controls(self, settings: dict[str, Any]) -> None:
        controls = self._get_common_controls(settings)
        controls.update(self._get_camera_specific_controls(settings))
        self._cam.set_controls(controls)

    def start(self, settings: dict[str, Any]) -> None:
        res = self._resolve_image_resolution(settings)
        self._cam = Picamera2()
        self._camera_config = self._cam.create_still_configuration(
            main={"format": "RGB888", "size": res}
        )
        self._logger.info("%s still config: %s", self._camera_name, str(self._camera_config.get("main")))
        self._cam.configure(self._camera_config)
        self._cam.start(show_preview=False)
        self._apply_runtime_controls(settings)

    def initialize(self, settings: dict[str, Any]) -> None:
        if self._cam is not None:
            self._apply_runtime_controls(settings)

    def update(self, context: Any = None) -> None:
        try:
            request = self._cam.capture_request()
            self._current_metadata = request.get_metadata()
            self._current_image = request.make_array("main")
            request.release()

            self._logger.debug("Current image size: %s", str(self._current_image.size))
            self._logger.debug("Current image buffer updated")
        except Exception:
            self._logger.warning("Failed to update image buffer", exc_info=True)
            self._current_image = None
            self._current_metadata = None

    def start_stream(self, settings: dict[str, Any] | None = None) -> None:
        if settings is None:
            settings = {}
        stream_res = self._resolve_stream_resolution(settings)
        self._cam = Picamera2()
        self._camera_config = self._cam.create_video_configuration(
            main={"format": "RGB888", "size": stream_res},
            controls=self._get_stream_controls(settings),
        )
        self._logger.info("%s stream config: %s", self._camera_name, str(self._camera_config.get("main")))
        self._cam.configure(self._camera_config)
        self._cam.start(show_preview=False)
        self._apply_runtime_controls(settings)

    def stop(self) -> None:
        if self._cam is not None:
            self._cam.stop()
            self._cam.close()
            self._cam = None

    def __del__(self):
        self.stop()
