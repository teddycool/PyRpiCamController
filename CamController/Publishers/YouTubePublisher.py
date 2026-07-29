# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import subprocess
import logging
import os
import threading
import time
import queue
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
        self.bitrate = "1500k"  # Reduced from 2500k for lower latency on Pi 3B+
        self.enabled = False

        self._ffmpeg_process = None
        self._retry_count = 0
        self._max_retries = 5
        self._retry_delay = 5.0  # seconds, grows with exponential backoff
        self._last_retry_time = 0.0
        self._connection_active = False
        self._lock = threading.Lock()
        self._stats_lock = threading.Lock()
        
        # Phase 2: Async frame publishing via queue (always initialized, worker thread started on demand)
        self._publish_queue = queue.Queue(maxsize=30)  # Drop frames if network/encoder can't keep up
        self._publish_thread = None
        self._publish_thread_stop = False
        
        self._stats = {
            "started_at": None,
            "frame_attempts": 0,
            "frame_published": 0,
            "frame_dropped": 0,
            "publish_errors": 0,
            "total_publish_time_ms": 0.0,
            "max_publish_time_ms": 0.0,
            "last_publish_time_ms": None,
            "last_success_time": None,
            "last_error": None,
            "last_frame_bytes": 0,
        }

        logger.debug("YouTubePublisher initialized")

    def _reset_stats(self):
        with self._stats_lock:
            self._stats = {
                "started_at": time.time(),
                "frame_attempts": 0,
                "frame_published": 0,
                "frame_dropped": 0,
                "publish_errors": 0,
                "total_publish_time_ms": 0.0,
                "max_publish_time_ms": 0.0,
                "last_publish_time_ms": None,
                "last_success_time": None,
                "last_error": None,
                "last_frame_bytes": 0,
            }

    def _note_stat_error(self, message: str):
        with self._stats_lock:
            self._stats["frame_dropped"] += 1
            self._stats["publish_errors"] += 1
            self._stats["last_error"] = message

    def get_stats(self):
        """Return a snapshot of YouTube performance metrics."""
        with self._stats_lock:
            stats = dict(self._stats)

        now = time.time()
        started_at = stats.get("started_at")
        runtime_seconds = max(0.0, now - started_at) if started_at else 0.0
        published = stats.get("frame_published", 0) or 0
        attempts = stats.get("frame_attempts", 0) or 0
        avg_publish_ms = (
            stats["total_publish_time_ms"] / published if published else 0.0
        )

        return {
            "enabled": self.enabled,
            "connection_active": self._connection_active,
            "runtime_seconds": round(runtime_seconds, 1),
            "frame_attempts": attempts,
            "frame_published": published,
            "frame_dropped": stats.get("frame_dropped", 0),
            "publish_errors": stats.get("publish_errors", 0),
            "published_fps": round(published / runtime_seconds, 2) if runtime_seconds > 0 else 0.0,
            "attempt_fps": round(attempts / runtime_seconds, 2) if runtime_seconds > 0 else 0.0,
            "avg_publish_ms": round(avg_publish_ms, 2),
            "max_publish_ms": round(stats.get("max_publish_time_ms", 0.0), 2),
            "last_publish_ms": stats.get("last_publish_time_ms"),
            "last_success_age_s": round(now - stats["last_success_time"], 1) if stats.get("last_success_time") else None,
            "last_error": stats.get("last_error"),
            "drop_rate_percent": round((stats.get("frame_dropped", 0) / attempts) * 100.0, 1) if attempts else 0.0,
            "retry_count": self._retry_count,
            "retry_delay_s": self._retry_delay,
            "process_pid": self._ffmpeg_process.pid if self._ffmpeg_process else None,
            "last_frame_bytes": stats.get("last_frame_bytes", 0),
        }

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
            self.bitrate = str(_setting_value(youtube_settings, "bitrate", "1500k") or "1500k")

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

            self._reset_stats()

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
            # Phase 1: ultrafast preset + lower bitrate for Pi 3B+ optimization
            bitrate_int = int(''.join(filter(str.isdigit, self.bitrate)) or '1500')
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
                "-preset", "ultrafast",         # Maximum speed for Pi 3B+; faster than 'faster' by ~30-50%
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
            
            # Phase 2: Start background publish thread for async frame delivery
            self._start_publish_thread()

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

    def _start_publish_thread(self):
        """Start the background thread that publishes frames from queue to FFmpeg."""
        if self._publish_thread is not None and self._publish_thread.is_alive():
            return  # Already running
        
        # Create frame queue: max 30 frames (3 sec at 10 FPS) to allow burst but drop old frames on overflow
        self._publish_queue = queue.Queue(maxsize=30)
        self._publish_thread_stop = False
        self._publish_thread = threading.Thread(
            target=self._publish_worker,
            daemon=False,
            name="YouTubePublishWorker"
        )
        self._publish_thread.start()
        logger.info("YouTube publish worker thread started")

    def _publish_worker(self):
        """Background worker thread: consume frames from queue and write to FFmpeg stdin."""
        logger.debug("YouTube publish worker running")
        while not self._publish_thread_stop:
            try:
                # Block with timeout to allow periodic checks
                frame_data = self._publish_queue.get(timeout=0.5)
                if frame_data is None:  # Sentinel to stop
                    break
                
                # Now do the blocking FFmpeg write in background thread (doesn't block capture)
                if not self._connection_active or self._ffmpeg_process is None:
                    with self._stats_lock:
                        self._stats["frame_dropped"] += 1
                        self._stats["publish_errors"] += 1
                    continue
                
                try:
                    publish_start = time.perf_counter()
                    self._ffmpeg_process.stdin.write(frame_data)
                    self._ffmpeg_process.stdin.flush()
                    publish_ms = (time.perf_counter() - publish_start) * 1000.0
                    
                    with self._stats_lock:
                        self._stats["frame_published"] += 1
                        self._stats["total_publish_time_ms"] += publish_ms
                        self._stats["max_publish_time_ms"] = max(
                            self._stats["max_publish_time_ms"],
                            publish_ms,
                        )
                        self._stats["last_publish_time_ms"] = round(publish_ms, 2)
                        self._stats["last_success_time"] = time.time()
                        self._stats["last_error"] = None
                        self._stats["last_frame_bytes"] = len(frame_data)
                    
                    # Log slow publishes (but less aggressively than before)
                    if publish_ms > 150.0:
                        logger.debug(
                            "YouTube publish slow (async worker): %.1f ms for %d bytes",
                            publish_ms,
                            len(frame_data),
                        )
                except BrokenPipeError:
                    logger.warning("FFmpeg pipe broken in publish worker")
                    with self._stats_lock:
                        self._stats["frame_dropped"] += 1
                        self._stats["publish_errors"] += 1
                        self._stats["last_error"] = "broken_pipe_worker"
                    self._connection_active = False
                    self._check_and_retry()
                except Exception as e:
                    logger.error("Publish worker error: %s", e)
                    with self._stats_lock:
                        self._stats["frame_dropped"] += 1
                        self._stats["publish_errors"] += 1
                        self._stats["last_error"] = str(e)
                    self._connection_active = False
                    self._check_and_retry()
            except queue.Empty:
                # Timeout waiting for frame — loop and check stop flag
                pass
            except Exception as e:
                logger.error("Unexpected error in publish worker: %s", e, exc_info=True)
                break
        
        logger.debug("YouTube publish worker exiting")

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
        Queue one JPEG frame for async publishing (non-blocking).
        
        Phase 2 optimization: This method no longer blocks on FFmpeg writes.
        Instead, it adds the frame to a queue that a background worker thread
        consumes. This allows the main capture thread to continue at full speed.

        Args:
            jpgimagedata: JPEG image data (bytes or bytearray)
            metadata:     Optional dict — not used for streaming, kept for API compat

        Returns:
            True if the frame was queued successfully, False otherwise
        """
        with self._stats_lock:
            self._stats["frame_attempts"] += 1
        
        if not self.enabled or not self._connection_active:
            self._note_stat_error("publisher_disabled_or_inactive")
            self._check_and_retry()
            return False
        
        if self._ffmpeg_process is None or self._ffmpeg_process.poll() is not None:
            poll_result = self._ffmpeg_process.poll() if self._ffmpeg_process else None
            logger.debug(
                "YouTubePublisher: FFmpeg not active (poll=%s), skipping frame",
                poll_result
            )
            self._connection_active = False
            self._note_stat_error(f"ffmpeg_inactive_poll={poll_result}")
            self._check_and_retry()
            return False
        
        # Convert to bytes if needed
        frame_data = bytes(jpgimagedata) if isinstance(jpgimagedata, bytearray) else jpgimagedata
        
        # Try to queue frame without blocking the main thread
        # If queue is full (backpressure), drop the oldest frame via Full exception
        try:
            self._publish_queue.put(frame_data, block=False)
            return True
        except queue.Full:
            # Queue full: network/encoder can't keep up, drop frame
            with self._stats_lock:
                self._stats["frame_dropped"] += 1
                self._stats["publish_errors"] += 1
                self._stats["last_error"] = "queue_full_dropped"
            logger.debug("YouTube publish queue full, dropping frame (network congestion)")
            return False
        except Exception as e:
            logger.error("Failed to queue frame to YouTube: %s", e, exc_info=True)
            self._connection_active = False
            self._note_stat_error(str(e))
            self._check_and_retry()
            return False

    def cleanup(self):
        """Stop FFmpeg, publish worker thread, and release all resources."""
        logger.info("YouTubePublisher cleanup...")
        try:
            # Stop the publish worker thread first
            if self._publish_thread is not None:
                self._publish_thread_stop = True
                if self._publish_queue is not None:
                    try:
                        self._publish_queue.put(None, block=False)  # Sentinel to wake up worker
                    except queue.Full:
                        pass
                try:
                    self._publish_thread.join(timeout=2)
                    logger.info("Publish worker thread stopped")
                except Exception as e:
                    logger.warning("Error stopping publish thread: %s", e)
                self._publish_thread = None
            
            # Now stop FFmpeg
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
