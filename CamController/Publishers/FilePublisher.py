# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import os
import time
import json
import logging

#TODO: how to handle when storage starts to fill up? Delete oldest files?


from .PublisherBase import PublisherBase

logger = logging.getLogger("cam.publisher.file")

class FilePublisher(PublisherBase):
    def __init__(self):
        self.location = "home/pi/shared/images/"
        self.img_format = "jpg"  # Default image format
        logger.debug("Init FilePublisher")

    def initialize(self, settings):
        # Update location from settings if available
        self.location = settings.get("Cam", {}).get("publishers", {}).get("file", {}).get("location", self.location)
        os.makedirs(self.location, exist_ok=True)

        self.img_format = settings.get("Cam", {}).get("publishers", {}).get("file", {}).get("format", self.img_format)
        
        if self.img_format not in ["jpg"]:
            raise ValueError(f"Unsupported image format: {self.img_format}. Supported formats: jpg.")
        logger.info(f"FilePublisher initialized with location: {self.location} and format: {self.img_format}")  

    def publish(self, jpgimagedata, metadata):
        try:
            timestamp = int(time.time())
            img_filename = os.path.join(self.location, f"{timestamp}.{self.img_format}")
            meta_filename = os.path.join(self.location, f"{timestamp}.json")

            # Write image data to file
            with open(img_filename, "wb") as img_file:
                img_file.write(jpgimagedata.tobytes())

            # Write metadata to JSON file
            with open(meta_filename, "w") as meta_file:
                json.dump(metadata, meta_file, indent=2)

            logger.debug(f"Saved image to {img_filename} and metadata to {meta_filename}")
        except Exception as e:
            logger.error(f"FilePublisher failed to save image or metadata: {e}", exc_info=True)