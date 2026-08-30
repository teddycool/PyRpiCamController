# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import time
import threading
from CamStates import BaseState
from StreamingServer import ModernStreamingServer
import logging

logger = logging.getLogger("cam.state.streamstate")


class StreamState(BaseState.BaseState):
    def __init__(self):
        super(StreamState, self).__init__()
        self._streaming_server = None
        self._last_health_check = 0.0
        self._health_check_interval = 3.0

        # YouTube Live forwarding
        self._youtube_publisher = None
        self._youtube_forward_running = False
        self._youtube_forward_thread = None
        self._last_youtube_frame = 0.0
        self._youtube_frame_interval = 0.1          # ~10 FPS to YouTube
        self._youtube_frame_interval_with_clients = 0.2  # Relax when local viewers active
        self._youtube_stats_lock = threading.Lock()
        self._youtube_forward_frames_seen = 0
        self._youtube_forward_frames_sent = 0
        self._youtube_forward_frames_skipped = 0
        self._youtube_forward_errors = 0

        # Local stream recording forwarding
        self._recorder_publisher = None
        self._recorder_forward_running = False
        self._recorder_forward_thread = None
        self._recorder_stats_lock = threading.Lock()
        self._recorder_forward_frames_seen = 0
        self._recorder_forward_frames_sent = 0
        self._recorder_forward_errors = 0
        return

    def initialize(self, settings):
        """Initialize streaming state with camera and server"""
        super().initialize(settings)
        logger.info("StreamState initialize...")
        self._last_health_check = 0.0
        self._health_check_interval = float(settings.get("Stream.health_check_interval", 3.0))
        
        try:
            logger.info(f"Starting streaming with settings: CamChip={settings.get('CamChip', 'Unknown')}")
            
            # Start streaming with the modern streaming server
            success = ModernStreamingServer.start_streaming(settings)
            
            if success:
                logger.info("Streaming server started successfully")
                self._streaming_server = ModernStreamingServer.streaming_instance
            else:
                logger.error("Failed to start streaming server")
                raise Exception("Streaming server initialization failed")

            # --- YouTube Live publisher ---
            self._last_youtube_frame = 0.0
            with self._youtube_stats_lock:
                self._youtube_forward_frames_seen = 0
                self._youtube_forward_frames_sent = 0
                self._youtube_forward_frames_skipped = 0
                self._youtube_forward_errors = 0
            with self._recorder_stats_lock:
                self._recorder_forward_frames_seen = 0
                self._recorder_forward_frames_sent = 0
                self._recorder_forward_errors = 0
            self._youtube_frame_interval = float(settings.get("Stream.youtube_frame_interval", 0.0))
            self._youtube_frame_interval_with_clients = float(
                settings.get("Stream.youtube_frame_interval_with_clients", 0.0)
            )

            # Derive frame interval from configured YouTube FPS if not explicitly set.
            youtube_fps_raw = settings.get("Cam", {}).get("publishers", {}).get("youtube", {}).get("fps", {})
            if isinstance(youtube_fps_raw, dict):
                youtube_fps_raw = youtube_fps_raw.get("value", 10)
            try:
                youtube_fps = max(1, int(youtube_fps_raw))
            except (TypeError, ValueError):
                youtube_fps = 10
            derived_interval = round(1.0 / youtube_fps, 6)

            if self._youtube_frame_interval <= 0:
                self._youtube_frame_interval = derived_interval
            # Clamp: never faster than configured fps, never slower than 1 fps
            self._youtube_frame_interval = max(derived_interval, min(self._youtube_frame_interval, 1.0))
            # Relaxed-client interval is unused now but kept for stats display
            self._youtube_frame_interval_with_clients = self._youtube_frame_interval

            youtube_settings = settings.get("Cam", {}).get("publishers", {}).get("youtube", {})
            youtube_enabled = False
            if isinstance(youtube_settings, dict):
                pub = youtube_settings.get("publish", {})
                youtube_enabled = pub.get("value", False) if isinstance(pub, dict) else bool(pub)

            if youtube_enabled:
                try:
                    from Publishers.YouTubePublisher import YouTubePublisher
                    self._youtube_publisher = YouTubePublisher()
                    self._youtube_publisher.initialize(settings)
                    if getattr(self._youtube_publisher, "enabled", False):
                        if self._streaming_server and hasattr(self._streaming_server, "set_force_active_framerate"):
                            self._streaming_server.set_force_active_framerate(True)
                        logger.info(
                            "YouTube Live publisher active — frame_interval=%.3fs, "
                            "frame_interval_with_clients=%.3fs",
                            self._youtube_frame_interval,
                            self._youtube_frame_interval_with_clients,
                        )
                        self._start_youtube_forwarder()
                    else:
                        logger.info("YouTube publisher disabled or not fully configured")
                        self._youtube_publisher = None
                except Exception as e:
                    logger.error("Failed to initialize YouTube publisher: %s", e, exc_info=True)
                    self._youtube_publisher = None
            else:
                logger.info("YouTube Live disabled in settings")
                self._youtube_publisher = None

            recorder_settings = settings.get("Cam", {}).get("publishers", {}).get("recorder", {})
            recorder_enabled = False
            if isinstance(recorder_settings, dict):
                recorder_publish = recorder_settings.get("publish", {})
                recorder_enabled = (
                    recorder_publish.get("value", False)
                    if isinstance(recorder_publish, dict)
                    else bool(recorder_publish)
                )

            if recorder_enabled:
                try:
                    from Publishers.RecorderPublisher import RecorderPublisher
                    self._recorder_publisher = RecorderPublisher()
                    self._recorder_publisher.initialize(settings)
                    if getattr(self._recorder_publisher, "enabled", False):
                        logger.info("Local stream recorder active")
                        self._start_recorder_forwarder()
                    else:
                        logger.info("Recorder publisher disabled or not fully configured")
                        self._recorder_publisher = None
                except Exception as e:
                    logger.error("Failed to initialize recorder publisher: %s", e, exc_info=True)
                    self._recorder_publisher = None
            else:
                logger.info("Local stream recorder disabled in settings")
                self._recorder_publisher = None

            self._update_force_active_framerate()

        except Exception as e:
            logger.error(f"StreamState initialization failed: {e}", exc_info=True)
            raise

        return

    def _start_youtube_forwarder(self):
        """Start the background thread that feeds encoded frames to YouTube."""
        if self._youtube_forward_running:
            return

        self._youtube_forward_running = True

        def _forward_loop():
            logger.info("YouTube forwarder thread started")
            # Track the last frame object we forwarded by identity to avoid
            # re-processing the same frame when condition.notify_all() wakes us
            # due to an MJPEG client poll rather than a genuinely new frame.
            last_forwarded_frame = None

            while self._youtube_forward_running and self._youtube_publisher:
                try:
                    output = self._streaming_server.output if self._streaming_server else None
                    if output is None:
                        time.sleep(0.1)
                        continue

                    # Wait for a new frame. Use a short timeout so we stay
                    # responsive to stop requests without polling too hard.
                    with output.condition:
                        output.condition.wait(timeout=0.5)
                        frame = output.frame

                    if frame is None or frame is last_forwarded_frame:
                        # No new frame yet — loop back without counting a skip.
                        continue

                    with self._youtube_stats_lock:
                        self._youtube_forward_frames_seen += 1

                    # Send every frame to FFmpeg — no Python-side rate limiting.
                    # FFmpeg has `-r <fps>` on the output side and will pick the
                    # right frames and assign perfectly-spaced PTS timestamps.
                    # Python-side skipping introduces irregular delivery intervals
                    # which cause PTS drift and YouTube quality degradation.
                    published = self._youtube_publisher.publish(frame, metadata={"mode": "stream"})
                    if published:
                        last_forwarded_frame = frame
                        with self._youtube_stats_lock:
                            self._youtube_forward_frames_sent += 1

                except Exception as e:
                    with self._youtube_stats_lock:
                        self._youtube_forward_errors += 1
                    logger.warning("YouTube forwarder error: %s", e)
                    time.sleep(0.2)

            logger.info("YouTube forwarder thread stopped")

        self._youtube_forward_thread = threading.Thread(
            target=_forward_loop,
            name="youtube-forwarder",
            daemon=True,
        )
        self._youtube_forward_thread.start()

    def _start_recorder_forwarder(self):
        """Start the background thread that feeds encoded frames to local recorder."""
        if self._recorder_forward_running:
            return

        self._recorder_forward_running = True

        def _forward_loop():
            logger.info("Recorder forwarder thread started")
            last_forwarded_frame = None

            while self._recorder_forward_running and self._recorder_publisher:
                try:
                    output = self._streaming_server.output if self._streaming_server else None
                    if output is None:
                        time.sleep(0.1)
                        continue

                    with output.condition:
                        output.condition.wait(timeout=0.5)
                        frame = output.frame

                    if frame is None or frame is last_forwarded_frame:
                        continue

                    with self._recorder_stats_lock:
                        self._recorder_forward_frames_seen += 1

                    published = self._recorder_publisher.publish(frame, metadata={"mode": "stream"})
                    if published:
                        last_forwarded_frame = frame
                        with self._recorder_stats_lock:
                            self._recorder_forward_frames_sent += 1

                except Exception as e:
                    with self._recorder_stats_lock:
                        self._recorder_forward_errors += 1
                    logger.warning("Recorder forwarder error: %s", e)
                    time.sleep(0.2)

            logger.info("Recorder forwarder thread stopped")

        self._recorder_forward_thread = threading.Thread(
            target=_forward_loop,
            name="recorder-forwarder",
            daemon=True,
        )
        self._recorder_forward_thread.start()

    def _update_force_active_framerate(self):
        """Keep encoded stream FPS active while YouTube or recorder is running."""
        if not self._streaming_server or not hasattr(self._streaming_server, "set_force_active_framerate"):
            return

        youtube_active = bool(self._youtube_publisher and self._youtube_forward_running)
        recorder_active = bool(self._recorder_publisher and self._recorder_forward_running)
        self._streaming_server.set_force_active_framerate(youtube_active or recorder_active)

    def _stop_youtube(self):
        """Stop the YouTube forwarder thread and clean up the publisher."""
        self._youtube_forward_running = False
        if self._youtube_forward_thread and self._youtube_forward_thread.is_alive():
            self._youtube_forward_thread.join(timeout=2.0)
        self._youtube_forward_thread = None

        if self._youtube_publisher:
            try:
                self._youtube_publisher.cleanup()
                logger.info("YouTube publisher cleaned up")
            except Exception as e:
                logger.warning("Error cleaning up YouTube publisher: %s", e)
            self._youtube_publisher = None

        self._update_force_active_framerate()

    def _stop_recorder(self):
        """Stop local recorder forwarder thread and clean up the publisher."""
        self._recorder_forward_running = False
        if self._recorder_forward_thread and self._recorder_forward_thread.is_alive():
            self._recorder_forward_thread.join(timeout=2.0)
        self._recorder_forward_thread = None

        if self._recorder_publisher:
            try:
                self._recorder_publisher.cleanup()
                logger.info("Recorder publisher cleaned up")
            except Exception as e:
                logger.warning("Error cleaning up recorder publisher: %s", e)
            self._recorder_publisher = None

        self._update_force_active_framerate()

    def get_youtube_stats(self):
        """Return a combined snapshot of YouTube forwarder and publisher performance."""
        with self._youtube_stats_lock:
            forwarder_stats = {
                "forwarder_running": self._youtube_forward_running,
                "frame_interval": self._youtube_frame_interval,
                "frame_interval_with_clients": self._youtube_frame_interval_with_clients,
                "frames_seen": self._youtube_forward_frames_seen,
                "frames_sent": self._youtube_forward_frames_sent,
                "frames_skipped": self._youtube_forward_frames_skipped,
                "forward_errors": self._youtube_forward_errors,
            }

        publisher_stats = None
        if self._youtube_publisher and hasattr(self._youtube_publisher, "get_stats"):
            try:
                publisher_stats = self._youtube_publisher.get_stats()
            except Exception as e:
                logger.debug("Failed to collect YouTube publisher stats: %s", e)

        return {
            "enabled": bool(self._youtube_publisher and getattr(self._youtube_publisher, "enabled", False)),
            "running": bool(self._youtube_forward_running and self._youtube_publisher),
            "frame_interval": self._youtube_frame_interval,
            "frame_interval_with_clients": self._youtube_frame_interval_with_clients,
            "forwarder": forwarder_stats,
            "publisher": publisher_stats,
        }

    def get_recorder_stats(self):
        """Return a combined snapshot of recorder forwarder and publisher performance."""
        with self._recorder_stats_lock:
            forwarder_stats = {
                "forwarder_running": self._recorder_forward_running,
                "frames_seen": self._recorder_forward_frames_seen,
                "frames_sent": self._recorder_forward_frames_sent,
                "forward_errors": self._recorder_forward_errors,
            }

        publisher_stats = None
        if self._recorder_publisher and hasattr(self._recorder_publisher, "get_stats"):
            try:
                publisher_stats = self._recorder_publisher.get_stats()
            except Exception as e:
                logger.debug("Failed to collect recorder publisher stats: %s", e)

        return {
            "enabled": bool(self._recorder_publisher and getattr(self._recorder_publisher, "enabled", False)),
            "running": bool(self._recorder_forward_running and self._recorder_publisher),
            "forwarder": forwarder_stats,
            "publisher": publisher_stats,
        }

    def get_runtime_status(self):
        """Return StreamState-owned status without coupling MainLoop to YouTube."""
        youtube_stats = self.get_youtube_stats()
        recorder_stats = self.get_recorder_stats()
        status = {}
        if youtube_stats:
            status["youtube"] = youtube_stats
        if recorder_stats:
            status["recorder"] = recorder_stats
        return status

    def get_metrics(self):
        """Return stream metrics owned by the streaming state."""
        stream_metrics = None
        if self._streaming_server and hasattr(self._streaming_server, "get_metrics"):
            try:
                stream_metrics = self._streaming_server.get_metrics()
            except Exception as e:
                logger.debug("Failed to collect streaming metrics: %s", e)

        camera_metrics = None
        if self._streaming_server and getattr(self._streaming_server, "cam", None) is not None:
            camera = self._streaming_server.cam
            if hasattr(camera, "get_metrics"):
                try:
                    camera_metrics = camera.get_metrics()
                except Exception as e:
                    logger.debug("Failed to collect camera metrics from StreamState camera: %s", e)

        youtube_stats = self.get_youtube_stats()
        recorder_stats = self.get_recorder_stats()

        metrics = {
            "stream": stream_metrics,
            "camera": camera_metrics,
            "youtube": youtube_stats,
            "recorder": recorder_stats,
        }
        return {key: value for key, value in metrics.items() if value is not None}

    def update(self, context):
        """Update streaming state - camera runs in background"""
        now = time.time()
        if now - self._last_health_check < self._health_check_interval:
            return
        self._last_health_check = now

        # Check if streaming is still active
        if not ModernStreamingServer.is_streaming():
            logger.warning("Streaming stopped unexpectedly")
            # Could trigger state change back to PostState here
        return
    
    def cleanup(self):
        """Release streaming resources before reload or state transition."""
        logger.info("StreamState cleanup for settings reload...")
        self.stop_streaming()
    
    def stop_streaming(self):
        """Completely stop streaming (for state changes)"""
        logger.info("StreamState stop_streaming...")
        try:
            self._stop_youtube()
            self._stop_recorder()
            ModernStreamingServer.stop_streaming()
            self._streaming_server = None
            logger.info("Streaming server stopped completely")
        except Exception as e:
            logger.error(f"Error stopping streaming server: {e}")

    def dispose(self):
        """Release streaming resources during final shutdown."""
        self.stop_streaming()
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            self.stop_streaming()
        except:
            pass
