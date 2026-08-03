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
            self._youtube_frame_interval = float(settings.get("Stream.youtube_frame_interval", 0.1))
            self._youtube_frame_interval_with_clients = float(
                settings.get("Stream.youtube_frame_interval_with_clients", 0.2)
            )
            # Sanity-clamp: keep within 4–10 FPS range for YouTube compatibility
            self._youtube_frame_interval = max(0.1, min(self._youtube_frame_interval, 0.25))
            self._youtube_frame_interval_with_clients = max(
                self._youtube_frame_interval, self._youtube_frame_interval_with_clients
            )

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
            while self._youtube_forward_running and self._youtube_publisher:
                try:
                    output = self._streaming_server.output if self._streaming_server else None
                    if output is None:
                        time.sleep(0.1)
                        continue

                    # Wait for a new frame from the MJPEG buffer
                    with output.condition:
                        output.condition.wait(timeout=1.0)
                        frame = output.frame

                    if frame is None:
                        continue

                    with self._youtube_stats_lock:
                        self._youtube_forward_frames_seen += 1

                    published = self._youtube_publisher.publish(bytes(frame), metadata={"mode": "stream"})
                    if published:
                        self._last_youtube_frame = time.time()
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

        if self._streaming_server and hasattr(self._streaming_server, "set_force_active_framerate"):
            self._streaming_server.set_force_active_framerate(False)

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

    def get_runtime_status(self):
        """Return StreamState-owned status without coupling MainLoop to YouTube."""
        youtube_stats = self.get_youtube_stats()
        return {"youtube": youtube_stats} if youtube_stats else {}

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
