# Unit tests for camera interface integration after refactor
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project

import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'CamController'))

# Ensure imports succeed in environments without OpenCV.
if 'cv2' not in sys.modules:
    fake_cv2 = types.SimpleNamespace(
        imencode=lambda ext, img: (True, b'jpeg-bytes'),
    )
    sys.modules['cv2'] = fake_cv2

from CamStates.PostState import PostState
from StreamingServer import ModernStreamingServer as streaming_server_module


class _DummyDisplay:
    def image_post(self):
        return None

    def off(self):
        return None


class _DummyCam:
    def __init__(self, image, metadata):
        self.current_image = image
        self.current_metadata = metadata
        self.update_called = 0

    def update(self):
        self.update_called += 1


class _DummyPublisher:
    def __init__(self):
        self.calls = []

    def publish(self, image, metadata):
        self.calls.append((image, metadata))


class _DummyEncodedImage:
    pass


class TestPostStateCameraInterface:
    def test_update_uses_camera_interface_properties(self, monkeypatch):
        state = PostState()
        state._lastsent = 0
        state._refresh_publish_settings = lambda: None

        image_object = object()
        camera_metadata = {"ExposureTime": 100}
        state._cam = _DummyCam(image=image_object, metadata=camera_metadata)

        enriched_metadata = {"processors": {"mock": {"motion_analysis": {"motion_detected": False, "changed_pixels": 0}}}}
        state._image_processor = SimpleNamespace(process=lambda img, meta: (img, enriched_metadata))

        publisher = _DummyPublisher()
        state._publishers = [publisher]

        monkeypatch.setattr('CamStates.PostState.settings_manager.get', lambda key: 0 if key == 'Cam.timeslot' else None)
        monkeypatch.setattr('CamStates.PostState.cv2.imencode', lambda ext, img: (True, _DummyEncodedImage()))

        context = SimpleNamespace(_display=_DummyDisplay())

        state.update(context)

        assert state._cam.update_called == 1
        assert len(publisher.calls) == 1

        _, published_metadata = publisher.calls[0]
        assert published_metadata["ExposureTime"] == 100
        assert "processors" in published_metadata

    def test_update_skips_publish_when_no_image(self, monkeypatch):
        state = PostState()
        state._lastsent = 0
        state._refresh_publish_settings = lambda: None
        state._cam = _DummyCam(image=None, metadata={"ExposureTime": 200})
        state._image_processor = SimpleNamespace(process=lambda img, meta: (img, {}))

        publisher = _DummyPublisher()
        state._publishers = [publisher]

        monkeypatch.setattr('CamStates.PostState.settings_manager.get', lambda key: 0 if key == 'Cam.timeslot' else None)

        context = SimpleNamespace(_display=_DummyDisplay())

        state.update(context)

        assert state._cam.update_called == 1
        assert len(publisher.calls) == 0


class TestModernStreamingServerCameraInterface:
    def test_initialize_uses_get_cam_and_start_stream(self, monkeypatch):
        streamer = streaming_server_module.CameraStreamer()

        fake_cam = MagicMock()

        def fake_settings_get(key):
            values = {
                'Stream.resolution': (1280, 720),
                'Stream.framerate': 20,
                'Stream.port': 8081,
            }
            return values[key]

        monkeypatch.setattr(streaming_server_module, 'OPENCV_AVAILABLE', True)
        monkeypatch.setattr(streaming_server_module.settings_manager, 'get', fake_settings_get)
        monkeypatch.setattr('Cam.CamBase.get_cam', lambda cam_chip: fake_cam)
        monkeypatch.setattr(streamer, '_start_server', lambda port: None)
        monkeypatch.setattr(streamer, '_start_cam_capture', lambda framerate: setattr(streamer, 'running', True))

        ok = streamer.initialize({'CamChip': 'PiCam3'})

        assert ok is True
        fake_cam.start_stream.assert_called_once()

        stream_settings = fake_cam.start_stream.call_args[0][0]
        assert stream_settings['Stream']['resolution'] == (1280, 720)
        assert stream_settings['Stream']['framerate'] == 20

    def test_stop_calls_cam_stop(self):
        streamer = streaming_server_module.CameraStreamer()
        fake_cam = MagicMock()

        streamer.cam = fake_cam
        streamer.running = True
        streamer.server = None

        streamer.stop()

        fake_cam.stop.assert_called_once()
        assert streamer.cam is None
