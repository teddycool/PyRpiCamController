# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import glob
import logging
import os
import queue
import subprocess
import threading
import time
import sys

from .PublisherBase import PublisherBase

logger = logging.getLogger("cam.publisher.recorder")


class RecorderPublisher(PublisherBase):
    """Record local MJPEG stream frames to segmented files on disk."""

    def __init__(self):
        self.enabled = False
        self.location = "/home/pi/shared/recordings"
        self.segment_seconds = 300
        self.max_segments = 288

        self._ffmpeg_process = None
        self._queue = queue.Queue(maxsize=20)
        self._writer_thread = None
        self._stderr_thread = None
        self._thread_stop = False
        self._last_retention_check = 0.0

        self._stats_lock = threading.Lock()
        self._stats = {
            "started_at": None,
            "publish_attempts": 0,
            "frames_written": 0,
            "frames_dropped": 0,
            "write_errors": 0,
            "last_error": None,
            "last_write_ms": None,
            "max_write_ms": 0.0,
            "segments_deleted": 0,
        }

    def _setting_value(self, source, key, default=None):
        if not isinstance(source, dict):
            return default
        raw = source.get(key, default)
        if isinstance(raw, dict):
            return raw.get("value", default)
        return raw

    def initialize(self, settings):
        recorder_settings = settings.get("Cam", {}).get("publishers", {}).get("recorder", {})

        self.enabled = bool(self._setting_value(recorder_settings, "publish", False))
        self.location = str(self._setting_value(recorder_settings, "location", self.location) or self.location)

        try:
            self.segment_seconds = max(30, int(self._setting_value(recorder_settings, "segment_seconds", self.segment_seconds)))
        except (TypeError, ValueError):
            self.segment_seconds = 300

        try:
            self.max_segments = max(10, int(self._setting_value(recorder_settings, "max_segments", self.max_segments)))
        except (TypeError, ValueError):
            self.max_segments = 288

        if not self.enabled:
            logger.info("Recorder publisher is disabled")
            return

        os.makedirs(self.location, exist_ok=True)
        with self._stats_lock:
            self._stats["started_at"] = time.time()

        logger.info(
            "Recorder publisher enabled: location=%s segment_seconds=%s max_segments=%s",
            self.location,
            self.segment_seconds,
            self.max_segments,
        )

        self._start_ffmpeg_process()
        self._start_threads()

    def _start_ffmpeg_process(self):
        if self._ffmpeg_process is not None:
            try:
                self._ffmpeg_process.terminate()
                self._ffmpeg_process.wait(timeout=3)
            except Exception:
                try:
                    self._ffmpeg_process.kill()
                except Exception:
                    pass
            self._ffmpeg_process = None

        output_pattern = os.path.join(self.location, "stream_%Y%m%d_%H%M%S.mkv")
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-use_wallclock_as_timestamps", "1",
            "-f", "mjpeg",
            "-thread_queue_size", "16",
            "-i", "pipe:0",
            "-an",
            "-c:v", "copy",
            "-f", "segment",
            "-segment_time", str(self.segment_seconds),
            "-reset_timestamps", "1",
            "-strftime", "1",
            "-segment_format", "matroska",
            output_pattern,
        ]

        self._ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            bufsize=0,
            preexec_fn=os.setsid,
        )

        logger.info("Recorder FFmpeg started (PID: %d)", self._ffmpeg_process.pid)

    def _start_threads(self):
        if self._writer_thread is not None and self._writer_thread.is_alive():
            return

        self._thread_stop = False
        self._queue = queue.Queue(maxsize=20)

        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            name="RecorderWriteWorker",
            daemon=False,
        )
        self._writer_thread.start()

        self._stderr_thread = threading.Thread(
            target=self._stderr_loop,
            name="RecorderFfmpegStderr",
            daemon=True,
        )
        self._stderr_thread.start()

    def _stderr_loop(self):
        try:
            proc = self._ffmpeg_process
            if proc is None or proc.stderr is None:
                return
            for raw_line in proc.stderr:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                if line:
                    logger.warning("[ffmpeg] %s", line)
        except Exception:
            pass

    def _writer_loop(self):
        while not self._thread_stop:
            try:
                frame_data = self._queue.get(timeout=0.5)
                if frame_data is None:
                    break

                proc = self._ffmpeg_process
                if proc is None or proc.stdin is None or proc.poll() is not None:
                    self._restart_ffmpeg("ffmpeg_not_running")
                    with self._stats_lock:
                        self._stats["frames_dropped"] += 1
                        self._stats["write_errors"] += 1
                    continue

                start = time.perf_counter()
                proc.stdin.write(frame_data)
                write_ms = (time.perf_counter() - start) * 1000.0

                with self._stats_lock:
                    self._stats["frames_written"] += 1
                    self._stats["last_write_ms"] = round(write_ms, 2)
                    self._stats["max_write_ms"] = max(self._stats["max_write_ms"], write_ms)
                    self._stats["last_error"] = None

                if time.time() - self._last_retention_check >= 60:
                    self._last_retention_check = time.time()
                    self._apply_retention()

            except queue.Empty:
                continue
            except BrokenPipeError:
                self._restart_ffmpeg("broken_pipe")
                with self._stats_lock:
                    self._stats["frames_dropped"] += 1
                    self._stats["write_errors"] += 1
            except Exception as e:
                with self._stats_lock:
                    self._stats["frames_dropped"] += 1
                    self._stats["write_errors"] += 1
                    self._stats["last_error"] = str(e)
                logger.warning("Recorder write error: %s", e)
                self._restart_ffmpeg("write_exception")

    def _restart_ffmpeg(self, reason):
        logger.warning("Recorder FFmpeg restart requested: %s", reason)
        try:
            self._start_ffmpeg_process()
        except Exception as e:
            with self._stats_lock:
                self._stats["last_error"] = f"restart_failed:{e}"
            logger.error("Recorder FFmpeg restart failed: %s", e)

    def _apply_retention(self):
        try:
            pattern = os.path.join(self.location, "stream_*.mkv")
            files = sorted(glob.glob(pattern), key=os.path.getmtime)
            overflow = len(files) - self.max_segments
            if overflow <= 0:
                return

            deleted = 0
            for file_path in files[:overflow]:
                try:
                    os.remove(file_path)
                    deleted += 1
                except OSError:
                    continue

            if deleted:
                with self._stats_lock:
                    self._stats["segments_deleted"] += deleted
                logger.info("Recorder retention deleted %d old segment(s)", deleted)
        except Exception as e:
            logger.debug("Recorder retention check failed: %s", e)

    def publish(self, jpgimagedata, metadata=None):
        if not self.enabled:
            return False

        with self._stats_lock:
            self._stats["publish_attempts"] += 1

        if hasattr(jpgimagedata, "tobytes"):
            frame_data = jpgimagedata.tobytes()
        elif isinstance(jpgimagedata, (bytes, bytearray, memoryview)):
            frame_data = bytes(jpgimagedata)
        else:
            with self._stats_lock:
                self._stats["frames_dropped"] += 1
                self._stats["write_errors"] += 1
                self._stats["last_error"] = "unsupported_frame_type"
            return False

        try:
            self._queue.put(frame_data, block=False)
            return True
        except queue.Full:
            drained = 0
            while True:
                try:
                    self._queue.get_nowait()
                    drained += 1
                except queue.Empty:
                    break
            try:
                self._queue.put(frame_data, block=False)
            except queue.Full:
                drained += 1
            with self._stats_lock:
                self._stats["frames_dropped"] += drained
                self._stats["write_errors"] += 1
                self._stats["last_error"] = f"queue_drained_{drained}"
            logger.warning("Recorder queue overflow — drained %d stale frame(s)", drained)
            return False
        except Exception as e:
            with self._stats_lock:
                self._stats["frames_dropped"] += 1
                self._stats["write_errors"] += 1
                self._stats["last_error"] = str(e)
            return False

    def get_stats(self):
        with self._stats_lock:
            stats = dict(self._stats)

        runtime = 0.0
        if stats.get("started_at"):
            runtime = max(0.0, time.time() - stats["started_at"])

        return {
            "enabled": self.enabled,
            "location": self.location,
            "segment_seconds": self.segment_seconds,
            "max_segments": self.max_segments,
            "runtime_seconds": round(runtime, 1),
            "publish_attempts": stats.get("publish_attempts", 0),
            "frames_written": stats.get("frames_written", 0),
            "frames_dropped": stats.get("frames_dropped", 0),
            "write_errors": stats.get("write_errors", 0),
            "last_write_ms": stats.get("last_write_ms"),
            "max_write_ms": round(stats.get("max_write_ms", 0.0), 2),
            "segments_deleted": stats.get("segments_deleted", 0),
            "last_error": stats.get("last_error"),
            "process_pid": self._ffmpeg_process.pid if self._ffmpeg_process else None,
        }

    def get_metrics(self):
        return self.get_stats()

    def cleanup(self):
        self._thread_stop = True

        if self._queue is not None:
            try:
                self._queue.put(None, block=False)
            except queue.Full:
                pass

        if self._writer_thread is not None and self._writer_thread.is_alive():
            try:
                self._writer_thread.join(timeout=2)
            except Exception:
                pass
        self._writer_thread = None

        if self._ffmpeg_process is not None:
            try:
                if self._ffmpeg_process.stdin:
                    self._ffmpeg_process.stdin.close()
                self._ffmpeg_process.wait(timeout=5)
            except Exception:
                try:
                    self._ffmpeg_process.kill()
                except Exception:
                    pass
            self._ffmpeg_process = None


sys.modules.setdefault("Publishers.RecorderPublisher", sys.modules[__name__])
sys.modules.setdefault("CamController.Publishers.RecorderPublisher", sys.modules[__name__])
