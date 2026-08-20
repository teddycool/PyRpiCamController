# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import CamBase
from Cam import camera_settings
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import libcamera
from typing import Any
import logging
logger = logging.getLogger("cam.PiCamHQ")


class PiCamHQ(CamBase.CamBase):
    def __init__(self) -> None:
        super().__init__()
        self._camera_name = "PiCamHQ"
        self._supported_image_resolutions = [
            (4056, 3040),
            (2028, 1520),
            (1920, 1080),
            (1332, 990),
            (1280, 720),
            (640, 480),
        ]
        self._supported_video_resolutions = [
            (1920, 1080),
            (1280, 720),
            (640, 480),
        ]
        self._cam = None
        self._camera_config = None
        self._logger = logger

    def _setting_or_default(self, settings: dict[str, Any], path: str, default: Any) -> Any:
        current: Any = settings
        for part in path.split('.'):
            if not isinstance(current, dict):
                return default
            current = current.get(part, default)

        if isinstance(current, dict):
            return current.get("value", default)
        return current

    def _resolve_awb_mode(self, settings: dict[str, Any]) -> Any:
        awb_mode_raw = str(
            self._setting_or_default(settings, "Cam.white_balance_mode", "auto") or "auto"
        ).strip().lower()

        mode_map = {
            "auto": libcamera.controls.AwbModeEnum.Auto,
            "daylight": libcamera.controls.AwbModeEnum.Daylight,
            "cloudy": libcamera.controls.AwbModeEnum.Cloudy,
            "tungsten": libcamera.controls.AwbModeEnum.Tungsten,
            "fluorescent": libcamera.controls.AwbModeEnum.Fluorescent,
            "indoor": libcamera.controls.AwbModeEnum.Indoor,
            "incandescent": libcamera.controls.AwbModeEnum.Incandescent,
        }
        return mode_map.get(awb_mode_raw, libcamera.controls.AwbModeEnum.Auto)

    def _video_color_space(self):
        color_space_factory = getattr(getattr(libcamera, "ColorSpace", None), "Sycc", None)
        if callable(color_space_factory):
            return color_space_factory()
        return None

    def _resolve_image_resolution(self, settings: dict[str, Any]) -> CamBase.Resolution:
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

    def _resolve_stream_resolution(self, settings: dict[str, Any]) -> CamBase.Resolution:
        stream_cfg = camera_settings.StreamSettings.from_settings(settings, self._supported_video_resolutions[0])
        requested_res = stream_cfg.resolution

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
        camera_cfg = camera_settings.CameraSettings.from_settings(settings, self._supported_image_resolutions[0])

        awb_enable = bool(self._setting_or_default(settings, "Cam.awb_enable", True))
        controls = {
            "AwbMode": self._resolve_awb_mode(settings),
            "AeEnable": True,
            "AwbEnable": awb_enable,
        }

        if camera_cfg.brightness is not None:
            controls["Brightness"] = camera_cfg.brightness

        saturation = self._setting_or_default(settings, "Cam.saturation", None)
        if saturation is not None:
            controls["Saturation"] = float(saturation)

        contrast = self._setting_or_default(settings, "Cam.contrast", None)
        if contrast is not None:
            controls["Contrast"] = float(contrast)

        sharpness = self._setting_or_default(settings, "Cam.sharpness", None)
        if sharpness is not None:
            controls["Sharpness"] = float(sharpness)

        if not awb_enable:
            red_gain = self._setting_or_default(settings, "Cam.white_balance_red_gain", None)
            blue_gain = self._setting_or_default(settings, "Cam.white_balance_blue_gain", None)
            if red_gain is not None and blue_gain is not None:
                controls["ColourGains"] = (float(red_gain), float(blue_gain))

        return controls

    def _get_camera_specific_controls(self, settings: dict[str, Any]) -> dict[str, Any]:
        return {}

    def _get_stream_controls(self, settings: dict[str, Any]) -> dict[str, Any]:
        stream_cfg = camera_settings.StreamSettings.from_settings(settings, self._supported_video_resolutions[0])
        return {
            "FrameRate": stream_cfg.framerate,
        }

    def _resolve_stream_mjpeg_bitrate(
        self,
        settings: dict[str, Any],
        resolution: CamBase.Resolution,
        framerate: int,
    ) -> int:
        manual_mbps = self._setting_or_default(settings, "Stream.mjpeg_bitrate_mbps", 0)
        try:
            manual_mbps_int = int(manual_mbps)
        except (TypeError, ValueError):
            manual_mbps_int = 0

        if manual_mbps_int > 0:
            bitrate = max(8_000_000, min(120_000_000, manual_mbps_int * 1_000_000))
            self._logger.info("%s MJPEG bitrate: manual %s Mbps", self._camera_name, bitrate // 1_000_000)
            return bitrate

        jpeg_quality = self._setting_or_default(settings, "Stream.jpeg_quality", 80)
        try:
            jpeg_quality_int = int(jpeg_quality)
        except (TypeError, ValueError):
            jpeg_quality_int = 80

        jpeg_quality_int = max(40, min(95, jpeg_quality_int))
        quality_factor = max(0.65, min(1.45, jpeg_quality_int / 80.0))
        width, height = int(resolution[0]), int(resolution[1])
        auto_bitrate = int(width * height * max(1, int(framerate)) * quality_factor)
        bitrate = max(8_000_000, min(80_000_000, auto_bitrate))
        self._logger.info(
            "%s MJPEG bitrate auto=%s Mbps (res=%sx%s fps=%s quality=%s)",
            self._camera_name,
            bitrate // 1_000_000,
            width,
            height,
            framerate,
            jpeg_quality_int,
        )
        return bitrate

    def _apply_runtime_controls(self, settings: dict[str, Any]) -> None:
        if self._cam is None:
            return
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
        stream_color_space = self._video_color_space()
        stream_config_kwargs = {"controls": self._get_stream_controls(settings)}
        if stream_color_space is not None:
            stream_config_kwargs["colour_space"] = stream_color_space
        self._camera_config = self._cam.create_video_configuration(
            main={"format": "RGB888", "size": stream_res},
            **stream_config_kwargs,
        )
        self._logger.info("%s stream config: %s", self._camera_name, str(self._camera_config.get("main")))
        self._cam.configure(self._camera_config)
        self._cam.start(show_preview=False)
        self._apply_runtime_controls(settings)

    def capture_stream_frame(self) -> Any:
        if self._cam is None:
            return None
        try:
            request = self._cam.capture_request()
            frame = request.make_array("main")
            request.release()
            self._current_image = frame
            return frame
        except Exception:
            self._logger.warning("Failed to capture stream frame", exc_info=True)
            return None

    def start_stream_encoded(self, settings: dict[str, Any], output: Any) -> bool:
        """Start camera with Picamera2 MJPEG encoder output for low CPU usage."""
        try:
            stream_res = self._resolve_stream_resolution(settings)
            stream_cfg = camera_settings.StreamSettings.from_settings(settings, self._supported_video_resolutions[0])
            stream_fps = max(1, int(stream_cfg.framerate))
            stream_bitrate = self._resolve_stream_mjpeg_bitrate(settings, stream_res, stream_fps)
            self._cam = Picamera2()
            stream_color_space = self._video_color_space()
            stream_config_kwargs = {"controls": self._get_stream_controls(settings)}
            if stream_color_space is not None:
                stream_config_kwargs["colour_space"] = stream_color_space
            self._camera_config = self._cam.create_video_configuration(
                main={"format": "YUV420", "size": stream_res},
                **stream_config_kwargs,
            )
            self._logger.info(
                "%s encoded stream config: %s",
                self._camera_name,
                str(self._camera_config.get("main")),
            )
            self._cam.configure(self._camera_config)
            encoder = MJPEGEncoder(bitrate=stream_bitrate)
            self._cam.start_recording(encoder, FileOutput(output))
            self._apply_runtime_controls(settings)
            return True
        except Exception:
            self._logger.warning("Failed to start encoded stream path", exc_info=True)
            return False

    def set_stream_framerate(self, framerate: int) -> bool:
        if self._cam is None:
            return False
        try:
            self._cam.set_controls({"FrameRate": int(framerate)})
            return True
        except Exception:
            self._logger.warning("Failed to set stream framerate", exc_info=True)
            return False

    def stop(self) -> None:
        if self._cam is not None:
            try:
                self._cam.stop_recording()
            except Exception:
                pass
            self._cam.stop()
            self._cam.close()
            self._cam = None

    def cleanup(self) -> None:
        self.stop()

    def dispose(self) -> None:
        self.stop()

    def __del__(self):
        self.stop()

    