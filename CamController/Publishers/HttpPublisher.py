# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import requests
import json
import logging

from Connectivity import cpuserial

from PublisherBase import PublisherBase

logger = logging.getLogger("cam.publisher.http")

class HttpPublisher(PublisherBase):
    def __init__(self, url):
        self.url = url
        self.cpuid = cpuserial.getserial()
        logger.info(f"HttpPublisher initialized with URL: {self.url} and CPU ID: {self.cpuid}")

    def initialize(self, settings):
        # Optionally update self.url or other settings from config
        self.url = settings.get("Cam", {}).get("posturl", self.url)

    def publish(self, jpgimagedata, metadata):
        try:        
            data = jpgimagedata.tobytes()
            files = {'media': data}
            url = self.url + '?cpu=' + self.cpuid + '&meta=' + json.dumps(metadata)
            r = requests.post(url, files=files)
            logger.debug("Posted image-data to " + url)
            logger.debug("Received http-status: " + str(r.status_code))
            return r.status_code
        except Exception as e:
            logger.error(f"HttpPublisher failed. Exception: {e}", exc_info=True)
            return None            # ...existing code...