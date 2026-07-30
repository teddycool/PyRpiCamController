# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import subprocess
import time

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'CamController'))

from Publishers.YouTubePublisher import YouTubePublisher


class TestYouTubePublisher:
    """Unit tests for YouTubePublisher."""

    def test_init(self):
        publisher = YouTubePublisher()
        assert publisher.enabled is False
        assert publisher.rtmps_url == ""
        assert publisher.stream_key == ""
        assert publisher.bitrate == "1500k"  # Phase 1: reduced bitrate for Pi 3B+
        assert publisher.fps == 10
        assert publisher._ffmpeg_process is None
        assert publisher._connection_active is False

    def test_get_stats_snapshot(self):
        publisher = YouTubePublisher()
        publisher.enabled = True
        publisher._connection_active = True

        with publisher._stats_lock:
            publisher._stats["started_at"] = time.time() - 10.0
            publisher._stats["frame_attempts"] = 10
            publisher._stats["frame_published"] = 8
            publisher._stats["frame_dropped"] = 2
            publisher._stats["publish_errors"] = 1
            publisher._stats["total_publish_time_ms"] = 80.0
            publisher._stats["max_publish_time_ms"] = 15.5
            publisher._stats["last_publish_time_ms"] = 9.5

        stats = publisher.get_stats()

        assert stats["frame_attempts"] == 10
        assert stats["frame_published"] == 8
        assert stats["frame_dropped"] == 2
        assert stats["published_fps"] > 0
        assert stats["avg_publish_ms"] == 10.0
        assert stats["max_publish_ms"] == 15.5

    def test_initialize_disabled(self):
        publisher = YouTubePublisher()
        settings = {"Cam": {"publishers": {"youtube": {"publish": {"value": False}}}}}
        publisher.initialize(settings)
        assert publisher.enabled is False

    def test_initialize_missing_url_and_key(self):
        publisher = YouTubePublisher()
        settings = {
            "Cam": {"publishers": {"youtube": {
                "publish": {"value": True},
                "rtmps_url": {"value": ""},
                "stream_key": {"value": ""},
            }}}
        }
        publisher.initialize(settings)
        assert publisher.enabled is False

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_initialize_success(self, mock_popen):
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_popen.return_value = mock_process

        publisher = YouTubePublisher()
        settings = {
            "Cam": {"publishers": {"youtube": {
                "publish": {"value": True},
                "rtmps_url": {"value": "rtmps://a.rtmp.youtube.com/live2"},
                "stream_key": {"value": "xxxx-xxxx-xxxx-xxxx"},
                "bitrate": {"value": "2500k"},
                "fps": {"value": 15},
            }}}
        }
        publisher.initialize(settings)

        assert publisher.enabled is True
        assert publisher.bitrate == "2500k"
        assert publisher.fps == 15
        mock_popen.assert_called_once()

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_initialize_invalid_fps_falls_back_to_default(self, mock_popen):
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_popen.return_value = mock_process

        publisher = YouTubePublisher()
        settings = {
            "Cam": {"publishers": {"youtube": {
                "publish": {"value": True},
                "rtmps_url": {"value": "rtmps://a.rtmp.youtube.com/live2"},
                "stream_key": {"value": "xxxx-xxxx-xxxx-xxxx"},
                "fps": {"value": 17},
            }}}
        }

        publisher.initialize(settings)
        assert publisher.fps == 10

    def test_start_ffmpeg_not_found(self):
        with patch('Publishers.YouTubePublisher.subprocess.Popen', side_effect=FileNotFoundError):
            publisher = YouTubePublisher()
            publisher.rtmps_url = "rtmps://a.rtmp.youtube.com/live2"
            publisher.stream_key = "test_key"
            publisher._start_ffmpeg_process()
            assert publisher.enabled is False
            assert publisher._connection_active is False

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_publish_success(self, mock_popen):
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        publisher = YouTubePublisher()
        publisher.enabled = True
        publisher._ffmpeg_process = mock_process
        publisher._connection_active = True

        frame = b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9'
        result = publisher.publish(frame)

        # Phase 2: publish() now returns True to queue, doesn't write directly
        assert result is True
        # Verify frame was queued (not written directly)
        assert publisher._publish_queue.qsize() == 1
        queued_frame = publisher._publish_queue.get_nowait()
        assert queued_frame == frame

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_publish_broken_pipe(self, mock_popen):
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process still running
        mock_process.stdin.write.side_effect = BrokenPipeError

        publisher = YouTubePublisher()
        publisher.enabled = True
        publisher._ffmpeg_process = mock_process
        publisher._connection_active = True

        # Phase 2: publish() queues frame successfully; worker thread handles broken pipe
        result = publisher.publish(b'\xff\xd8' + b'\x00' * 10 + b'\xff\xd9')
        assert result is True
        assert publisher._publish_queue.qsize() == 1

    def test_publish_when_disabled(self):
        publisher = YouTubePublisher()
        publisher.enabled = False
        result = publisher.publish(b'\xff\xd8' + b'\x00' * 10 + b'\xff\xd9')
        assert result is False

    def test_bytearray_converted_to_bytes(self):
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        publisher = YouTubePublisher()
        publisher.enabled = True
        publisher._ffmpeg_process = mock_process
        publisher._connection_active = True

        frame = bytearray(b'\xff\xd8' + b'\x00' * 50 + b'\xff\xd9')
        publisher.publish(frame)

        # Phase 2: bytearray is converted and queued (not written directly)
        queued_frame = publisher._publish_queue.get_nowait()
        assert isinstance(queued_frame, bytes)

    def test_exponential_backoff(self):
        publisher = YouTubePublisher()
        assert publisher._retry_count == 0

        publisher._schedule_retry()
        assert publisher._retry_count == 1
        assert publisher._retry_delay == 5.0

        publisher._schedule_retry()
        assert publisher._retry_count == 2
        assert publisher._retry_delay == 10.0

        publisher._schedule_retry()
        assert publisher._retry_count == 3
        assert publisher._retry_delay == 20.0

    def test_max_retries_disables_publisher(self):
        publisher = YouTubePublisher()
        publisher.enabled = True
        for _ in range(6):
            publisher._schedule_retry()
        assert publisher.enabled is False

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_cleanup_graceful(self, mock_popen):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        publisher = YouTubePublisher()
        publisher.rtmps_url = "rtmps://a.rtmp.youtube.com/live2"
        publisher.stream_key = "test_key"
        publisher.enabled = True
        publisher._start_ffmpeg_process()
        publisher.cleanup()

        assert publisher._ffmpeg_process is None
        assert publisher.enabled is False
        mock_process.stdin.close.assert_called_once()

    @patch('Publishers.YouTubePublisher.subprocess.Popen')
    def test_cleanup_force_kill_on_timeout(self, mock_popen):
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired('ffmpeg', 5)
        mock_popen.return_value = mock_process

        publisher = YouTubePublisher()
        publisher._ffmpeg_process = mock_process
        publisher.enabled = True
        publisher.cleanup()

        assert publisher._ffmpeg_process is None
        mock_process.kill.assert_called_once()

    def test_dispose_calls_cleanup(self):
        publisher = YouTubePublisher()
        publisher.cleanup = MagicMock()
        publisher.dispose()
        publisher.cleanup.assert_called_once()

    def test_rtmps_host_normalisation(self):
        """rtmps.youtube.com host should be normalised to rtmp.youtube.com."""
        with patch('Publishers.YouTubePublisher.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 999
            mock_popen.return_value = mock_process

            publisher = YouTubePublisher()
            settings = {
                "Cam": {"publishers": {"youtube": {
                    "publish": {"value": True},
                    "rtmps_url": {"value": "rtmps://a.rtmps.youtube.com/live2"},
                    "stream_key": {"value": "test_key"},
                    "bitrate": {"value": "2500k"},
                }}}
            }
            publisher.initialize(settings)
            assert "a.rtmp.youtube.com" in publisher.rtmps_url
