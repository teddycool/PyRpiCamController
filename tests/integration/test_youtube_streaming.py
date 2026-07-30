# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'CamController'))
sys.path.insert(0, os.path.join(project_root, 'Settings'))

from Publishers.YouTubePublisher import YouTubePublisher


class TestYouTubePublisherIntegration:
    """Integration tests for YouTubePublisher with schema and settings layer."""

    def test_publisher_settings_in_schema(self):
        """Verify YouTube publisher settings are present in the settings schema."""
        from settings_manager import settings_manager

        schema = settings_manager.get_web_editable_schema()
        youtube_fields = [k for k in schema.keys() if 'Cam.publishers.youtube' in k]

        assert len(youtube_fields) >= 5, (
            f"Expected at least 5 YouTube settings in schema, found: {youtube_fields}"
        )
        # Verify required keys exist
        paths = set(youtube_fields)
        assert any('publish' in p for p in paths), "Missing 'publish' toggle"
        assert any('rtmps_url' in p for p in paths), "Missing 'rtmps_url'"
        assert any('stream_key' in p for p in paths), "Missing 'stream_key'"
        assert any('bitrate' in p for p in paths), "Missing 'bitrate'"
        assert any('fps' in p for p in paths), "Missing 'fps'"

    def test_stream_key_is_password_type(self):
        """stream_key field should be of type 'password' so the Web GUI hides it."""
        from settings_manager import settings_manager

        schema = settings_manager.get_web_editable_schema()
        key_field = schema.get('Cam.publishers.youtube.stream_key')
        assert key_field is not None, "stream_key field missing from schema"
        assert key_field.get('type') == 'password', (
            "stream_key must be type 'password' to prevent display in the UI"
        )

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_all_bitrate_options_initialize(self, mock_popen):
        """All four supported bitrate options should produce a valid publisher."""
        mock_process = MagicMock()
        mock_process.pid = 100
        mock_popen.return_value = mock_process

        for bitrate in ("1500k", "2500k", "4000k", "6000k"):
            publisher = YouTubePublisher()
            settings = {
                "Cam": {"publishers": {"youtube": {
                    "publish": {"value": True},
                    "rtmps_url": {"value": "rtmps://a.rtmp.youtube.com/live2"},
                    "stream_key": {"value": "test_key"},
                    "bitrate": {"value": bitrate},
                }}}
            }
            publisher.initialize(settings)
            assert publisher.bitrate == bitrate, f"Bitrate mismatch for {bitrate}"

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_publisher_default_bitrate(self, mock_popen):
        """Default bitrate should be 2500k when not specified."""
        mock_process = MagicMock()
        mock_process.pid = 200
        mock_popen.return_value = mock_process

        publisher = YouTubePublisher()
        settings = {
            "Cam": {"publishers": {"youtube": {
                "publish": {"value": True},
                "rtmps_url": {"value": "rtmps://a.rtmp.youtube.com/live2"},
                "stream_key": {"value": "test_key"},
                # bitrate omitted → should default to 1500k (Phase 1 optimization for Pi 3B+)
            }}}
        }
        publisher.initialize(settings)
        assert publisher.bitrate == "1500k"

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_all_fps_options_initialize(self, mock_popen):
        """All supported FPS options should produce a valid publisher."""
        mock_process = MagicMock()
        mock_process.pid = 201
        mock_popen.return_value = mock_process

        for fps in (5, 10, 15, 20):
            publisher = YouTubePublisher()
            settings = {
                "Cam": {"publishers": {"youtube": {
                    "publish": {"value": True},
                    "rtmps_url": {"value": "rtmps://a.rtmp.youtube.com/live2"},
                    "stream_key": {"value": "test_key"},
                    "fps": {"value": fps},
                }}}
            }
            publisher.initialize(settings)
            assert publisher.fps == fps, f"FPS mismatch for {fps}"

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_frame_publishing_flow(self, mock_popen):
        """Simulate a short frame publishing sequence with async queue."""
        mock_process = MagicMock()
        mock_process.pid = 300
        mock_process.poll.return_value = None  # Always running
        mock_popen.return_value = mock_process

        publisher = YouTubePublisher()
        publisher.rtmps_url = "rtmps://a.rtmp.youtube.com/live2"
        publisher.stream_key = "xxxx-xxxx-xxxx-xxxx"
        publisher.bitrate = "1500k"  # Phase 1 default
        publisher.enabled = True
        publisher._ffmpeg_process = mock_process
        publisher._connection_active = True

        fake_jpeg = b'\xff\xd8\xff\xe0' + b'\xab' * 500 + b'\xff\xd9'
        for _ in range(10):
            result = publisher.publish(fake_jpeg)
            # Phase 2: publish returns True when frame queued (not written directly)
            assert result is True

        # Phase 2: frames are queued, not directly written
        assert publisher._publish_queue.qsize() == 10
