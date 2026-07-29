# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import subprocess
import logging
import os
import threading
import time
from urllib.parse import urlparse, urlunparse
from .PublisherBase import PublisherBase

logger = logging.getLogger("cam.publisher.youtube")


class YouTubePublisher(PublisherBase):
    """
    Publishes camera stream to YouTube Live using FFmpeg RTMPS.

    This publisher:
    - Takes MJPEG frames from camera/streaming server
    - Pipes them to an FFmpeg process
    - Streams to YouTube via RTMPS (Secure RTMP)
    - Handles connection failures with exponential backoff retry

    Prerequisites:
    - ffmpeg must be installed on the Pi (included in install-all-optimized.py)
    - A valid YouTube Live RTMPS ingest URL and stream key from YouTube Studio
    """

    def __init__(self):
        self.rtmps_url = ""
        self.stream_key = ""
        self.bitrate = "2500k"
        self.enabled = False

        self._ffmpeg_process = None
        self._retry_count = 0
        self._max_retries = 5
        self._retry_delay = 5.0  # seconds, grows with exponential backoff
        self._last_retry_time = 0.0
        self._connection_active = False
        self._lock = threading.Lock()

        logger.debug("YouTubePublisher initialized")

    def initialize(self, settings):
        """
        Initialize YouTube publisher with settings.

        Args:
            settings: Settings dict containing Cam.publishers.youtube config
        """
        logger.info("YouTubePublisher initialize...")

        try:
            youtube_settings = settings.get("Cam", {}).get("publishers", {}).get("youtube", {})

            def _setting_value(source, key, default=None):
                """Extract value from either raw value or dict with 'value' key."""
                if not isinstance(source, dict):
                    return default
                raw = source.get(key, default)
                if isinstance(raw, dict):
                    return raw.get("value", default)
                return raw

            self.enabled = bool(_setting_value(youtube_settings, "publish", False))
            self.rtmps_url = str(_setting_value(youtube_settings, "rtmps_url", "") or "").strip()
            self.stream_key = str(_setting_value(youtube_settings, "stream_key", "") or "").strip()
            self.bitrate = str(_setting_value(youtube_settings, "bitrate", "2500k") or "2500k")

            # Normalize known YouTube ingest host variants to canonical host.
            # YouTube ingest is typically a.rtmp.youtube.com for both rtmp:// and rtmps://.
            try:
                parsed = urlparse(self.rtmps_url)
                if parsed.netloc in ("a.rtmps.youtube.com", "a.rtmp.youtube.com"):
                    self.rtmps_url = urlunparse(
                        (parsed.scheme, "a.rtmp.youtube.com", parsed.path,
                         parsed.params, parsed.query, parsed.fragment)
                    )
            except Exception:
                pass

            stream_key_mask = "set" if self.stream_key else "empty"
            logger.info(
                "YouTube settings loaded: enabled=%s, url=%s, stream_key=%s, bitrate=%s",
                self.enabled,
                self.rtmps_url,
                stream_key_mask,
                self.bitrate,
            )

            if not self.enabled:
                logger.info("YouTube publisher is disabled")
                return

            # Validate protocol - YouTube requires RTMPS (secure), not plain RTMP
            if self.rtmps_url and not self.rtmps_url.startswith('rtmps://'):
                logger.error(
                    "CRITICAL: YouTube URL must use RTMPS (secure), not RTMP. "
                    "Expected rtmps:// but got: %s — YouTube will reject this connection",
                    self.rtmps_url[:60]
                )

            # Require both URL and stream key to proceed
            if not self.rtmps_url or not self.stream_key:
                logger.warning("YouTube publisher: RTMPS URL or stream key not configured")
                self.enabled = False
                return

            logger.info("YouTube publisher configured with bitrate: %s", self.bitrate)
            self._retry_count = 0
            self._start_ffmpeg_process()

        except Exception as e:
            logger.error("YouTubePublisher initialization failed: %s", e, exc_info=True)
            self.enabled = False

    def _start_ffmpeg_process(self):
        """
        Start FFmpeg subprocess for RTMPS streaming.

        FFmpeg reads MJPEG frames from stdin and re-encodes to H.264/AAC,
        then pushes the FLV stream to YouTube via RTMPS.
        """
        try:
            # Terminate any existing process first
            if self._ffmpeg_process is not None:
                try:
                    self._ffmpeg_process.terminate()
                    self._ffmpeg_process.wait(timeout=5)
                except Exception as e:
                    logger.warning("Failed to terminate existing FFmpeg process: %s", e)
                    try:
                        self._ffmpeg_process.kill()
                    except Exception:
                        pass
                self._ffmpeg_process = None

            # Build the full RTMPS endpoint URL
            base_url = self.rtmps_url.rstrip('/')
            stream_key = self.stream_key.lstrip('/')
            full_url = f"{base_url}/{stream_key}"
            logger.info("YouTube FFmpeg target endpoint: %s/[stream_key]", base_url)

            # FFmpeg command:
            #  - Read MJPEG frames from stdin at ~10 fps
            #  - Add a silent stereo audio track (YouTube requires audio)
            #  - Encode video as H.264, audio as AAC
            #  - Output as FLV to RTMPS endpoint
            bitrate_int = int(''.join(filter(str.isdigit, self.bitrate)) or '2500')
            ffmpeg_cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "warning",
                "-re",                          # Read input at native framerate
                "-f", "mjpeg",                  # Input format: MJPEG
                "-r", "10",                     # Input framerate (~10 FPS)
                "-i", "pipe:0",                 # Read from stdin
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",  # Silent audio
                "-c:v", "libx264",              # Video codec: H.264
                "-pix_fmt", "yuv420p",          # YouTube-compatible pixel format
                "-profile:v", "main",
                "-g", "20",                     # 2 s GOP at 10 fps
                "-keyint_min", "20",
                "-sc_threshold", "0",
                "-b:v", self.bitrate,           # Target video bitrate
                "-maxrate", self.bitrate,
                "-bufsize", f"{bitrate_int * 4}k",  # Buffer = 4× bitrate for smooth output
                "-preset", "faster",            # Good quality/CPU tradeoff on Pi 4/5
                "-tune", "zerolatency",         # Low-latency streaming behaviour
                "-c:a", "aac",                  # Audio codec
                "-b:a", "96k",                  # Audio bitrate (silent source)
                "-f", "flv",                    # Output container: FLV (RTMPS-compatible)
                full_url,
            ]

            self._ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                preexec_fn=os.setsid,  # Own process group for clean teardown
            )

            self._connection_active = True
            self._retry_count = 0
            logger.info(
                "FFmpeg process started (PID: %d) for YouTube streaming",
                self._ffmpeg_process.pid
            )

        except FileNotFoundError:
            logger.error("FFmpeg not found — please install the ffmpeg package")
            self.enabled = False
            self._connection_active = False
        except Exception as e:
            logger.error("Failed to start FFmpeg process: %s", e, exc_info=True)
            self._connection_active = False
            self._schedule_retry()

    def _schedule_retry(self):
        """Schedule retry with exponential backoff (max 5 min between attempts)."""
        if self._retry_count < self._max_retries:
            self._retry_count += 1
            self._retry_delay = min(5.0 * (2 ** (self._retry_count - 1)), 300.0)
            self._last_retry_time = time.time()
            logger.warning(
                "YouTube connection failed. Retry %d/%d in %.1fs",
                self._retry_count, self._max_retries, self._retry_delay
            )
        else:
            logger.error(
                "YouTube publisher: Max retries (%d) exceeded. Disabling.",
                self._max_retries
            )
            self.enabled = False
            self._connection_active = False

    def _check_and_retry(self):
        """Check whether FFmpeg is still alive and restart if a retry is due."""
        if not self.enabled:
            return

        def _log_ffmpeg_stderr_tail():
            try:
                if self._ffmpeg_process and self._ffmpeg_process.stderr:
                    # Non-blocking read using os.read with O_NONBLOCK
                    import os
                    import fcntl
                    fd = self._ffmpeg_process.stderr.fileno()
                    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                    try:
                        data = os.read(fd, 4096)
                        if data:
                            logger.error("FFmpeg stderr: %s", data.decode("utf-8", errors="replace")[:1200])
                    except BlockingIOError:
                        pass  # Nothing to read right now
                    finally:
                        # Restore blocking mode
                        fcntl.fcntl(fd, fcntl.F_SETFL, flags)
            except Exception as read_err:
                logger.debug("Could not read FFmpeg stderr: %s", read_err)

        with self._lock:
            if self._ffmpeg_process is not None:
                poll_result = self._ffmpeg_process.poll()
                if poll_result is not None:
                    logger.error("FFmpeg process terminated with exit code: %s", poll_result)
                    _log_ffmpeg_stderr_tail()
                    self._connection_active = False
                    self._schedule_retry()
                    if time.time() - self._last_retry_time >= self._retry_delay:
                        logger.info("Attempting YouTube reconnection...")
                        self._start_ffmpeg_process()
            else:
                if not self._connection_active and time.time() - self._last_retry_time >= self._retry_delay:
                    logger.info("Attempting YouTube reconnection...")
                    self._start_ffmpeg_process()

    def publish(self, jpgimagedata, metadata=None):
        """
        Write one JPEG frame into the FFmpeg stdin pipe.

        Args:
            jpgimagedata: JPEG image data (bytes or bytearray)
            metadata:     Optional dict — not used for streaming, kept for API compat

        Returns:
            True if the frame was written successfully, False otherwise
        """
        if not self.enabled or not self._connection_active:
            self._check_and_retry()
            return False

        try:
            with self._lock:
                if self._ffmpeg_process is None or self._ffmpeg_process.poll() is not None:
                    poll_result = self._ffmpeg_process.poll() if self._ffmpeg_process else None
                    logger.warning(
                        "YouTubePublisher: FFmpeg not active (poll=%s), skipping frame",
                        poll_result
                    )
                    self._connection_active = False
                    self._check_and_retry()
                    return False

                frame_data = bytes(jpgimagedata) if isinstance(jpgimagedata, bytearray) else jpgimagedata
                self._ffmpeg_process.stdin.write(frame_data)
                self._ffmpeg_process.stdin.flush()
                return True

        except BrokenPipeError:
            logger.warning("FFmpeg pipe broken — connection lost")
            self._connection_active = False
            self._check_and_retry()
            return False
        except Exception as e:
            logger.error("Failed to publish frame to YouTube: %s", e, exc_info=True)
            self._connection_active = False
            self._check_and_retry()
            return False

    def cleanup(self):
        """Stop FFmpeg and release all resources."""
        logger.info("YouTubePublisher cleanup...")
        try:
            with self._lock:
                if self._ffmpeg_process is not None:
                    try:
                        logger.info("Closing FFmpeg stdin and waiting for process to exit...")
                        if self._ffmpeg_process.stdin:
                            self._ffmpeg_process.stdin.close()
                        self._ffmpeg_process.wait(timeout=5)
                        logger.info("FFmpeg process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning("FFmpeg did not exit in time, killing...")
                        try:
                            self._ffmpeg_process.kill()
                            self._ffmpeg_process.wait()
                        except Exception:
                            pass
                    except Exception as e:
                        logger.warning("Error closing FFmpeg: %s", e)
                self._ffmpeg_process = None
                self._connection_active = False
                self.enabled = False
        except Exception as e:
            logger.error("Error during YouTubePublisher cleanup: %s", e, exc_info=True)

    def dispose(self):
        """Alias for cleanup — called by publisher lifecycle manager."""
        self.cleanup()
