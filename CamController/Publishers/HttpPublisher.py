# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import time
import requests
import logging

from Connectivity import cpuserial

from .PublisherBase import PublisherBase

logger = logging.getLogger("cam.publisher.http")

class HttpPublisher(PublisherBase):
    def __init__(self, url=""):
        self.url = url
        self.cpuid = cpuserial.getserial()
        self._publish_attempts = 0
        self._publish_successes = 0
        self._publish_failures = 0
        self._last_status_code = None
        self._last_error = None
        self._last_publish_at = None
        logger.info(f"HttpPublisher initialized with URL: {self.url} and CPU ID: {self.cpuid}")

    def initialize(self, settings):
        # Update URL from unified settings schema
        self.url = settings.get("Cam", {}).get("publishers", {}).get("url", {}).get("location", self.url)

    def publish(self, jpgimagedata, metadata=None) -> bool:
        self._publish_attempts += 1
        try:        
            if not self.url:
                logger.error("HttpPublisher URL is not configured")
                self._publish_failures += 1
                self._last_error = "URL not configured"
                return False

            data = jpgimagedata.tobytes()
            files = {'media': data}
            url = self.url + '?cpu=' + self.cpuid
            r = requests.post(url, files=files, timeout=30)
            logger.debug("Posted image-data to " + url)
            logger.debug("Received http-status: " + str(r.status_code))
            self._last_status_code = r.status_code
            self._last_publish_at = time.time()
            if 200 <= r.status_code < 300:
                self._publish_successes += 1
                self._last_error = None
                return True
            self._publish_failures += 1
            self._last_error = f"HTTP {r.status_code}"
            return False
        except Exception as e:
            logger.error(f"HttpPublisher failed. Exception: {e}", exc_info=True)
            self._publish_failures += 1
            self._last_error = str(e)
            return False

    def get_metrics(self) -> dict[str, object]:
        """Return structured metrics for the HTTP publisher."""
        return {
            "configured": bool(self.url),
            "publish_attempts": self._publish_attempts,
            "publish_successes": self._publish_successes,
            "publish_failures": self._publish_failures,
            "last_status_code": self._last_status_code,
            "last_publish_at": self._last_publish_at,
            "last_error": self._last_error,
        }

    def cleanup(self) -> None:
        """Release publisher resources."""
