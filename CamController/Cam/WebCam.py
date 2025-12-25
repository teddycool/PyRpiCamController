# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import CamBase
import cv2
import time
import logging
import numpy as np
import json
import sys
import datetime

logger = logging.getLogger("cam.WebCam")

class WebCam(CamBase.CamBase):
    def __init__(self):
        super(WebCam, self).__init__()
        self._supportedImagesResolutions = [(1920, 1080), (1280, 720), (640, 480)]
        self._supportedVideoResolutions = [(1920, 1080), (1280, 720), (640, 480)]
        self._cam = None
        self._device_index = 0  # Default webcam device index
        return
    
    #Cam mode   
    def start(self, settings):
        res = tuple(settings["Cam"]["resolution"])

        if not self.iResSupported(res):
            logger.warning("Cam resolution " + str(res) + " requested in config, but not supported!")
            logger.info("Setting first valid res from list " + str(self._supportedImagesResolutions))
            res = self._supportedImagesResolutions[0]

        # Initialize the webcam
        self._cam = cv2.VideoCapture(self._device_index)
        
        if not self._cam.isOpened():
            logger.error("Could not open webcam device " + str(self._device_index))
            raise RuntimeError("Failed to open webcam")
            
        # Set camera properties
        self._cam.set(cv2.CAP_PROP_FRAME_WIDTH, res[0])
        self._cam.set(cv2.CAP_PROP_FRAME_HEIGHT, res[1])
        self._cam.set(cv2.CAP_PROP_FPS, 30)
        
        # Set brightness if available
        if "brightness" in settings["Cam"]:
            # OpenCV brightness is typically 0-100, convert if needed
            brightness = settings["Cam"]["brightness"]
            if brightness < 0:
                brightness = 0
            elif brightness > 100:
                brightness = 100
            self._cam.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
        
        # Verify actual resolution set
        actual_width = int(self._cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info("Webcam initialized with resolution: {}x{}".format(actual_width, actual_height))
        
        # Warm up the camera
        for i in range(5):
            ret, frame = self._cam.read()
            time.sleep(0.1)
    
    def initialize(self, settings):
        # Webcam settings can be changed on the fly
        if self._cam is not None and self._cam.isOpened():
            if "brightness" in settings["Cam"]:
                brightness = settings["Cam"]["brightness"]
                if brightness < 0:
                    brightness = 0
                elif brightness > 100:
                    brightness = 100
                self._cam.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
        
    def update(self):
        try:
            if self._cam is None or not self._cam.isOpened():
                logger.error("Webcam is not initialized or opened")
                self._currentimg = None
                self._currentMetaData = None
                return
                
            ret, frame = self._cam.read()
            
            if not ret:
                logger.warning("Failed to capture frame from webcam")
                self._currentimg = None
                self._currentMetaData = None
                return
                
            # Convert from BGR (OpenCV default) to RGB 
            self._currentimg = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create metadata similar to Pi camera
            self._currentMetaData = {
                "timestamp": datetime.datetime.now().isoformat(),
                "ExposureTime": int(self._cam.get(cv2.CAP_PROP_EXPOSURE)) if self._cam.get(cv2.CAP_PROP_EXPOSURE) != -1 else 0,
                "FrameWidth": int(self._cam.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "FrameHeight": int(self._cam.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "Brightness": int(self._cam.get(cv2.CAP_PROP_BRIGHTNESS)) if self._cam.get(cv2.CAP_PROP_BRIGHTNESS) != -1 else 0,
                "CameraType": "WebCam"
            }
             
            logger.debug("Current image size: " + str(self._currentimg.size)) 
            logger.debug("Current image buffer updated")   
            logger.debug("Current metadata: " + json.dumps(self._currentMetaData))
            
        except Exception as e:
            logger.warning("Failed to update image buffer: %s" % str(e))
            self._currentimg = None
            self._currentMetaData = None
        
    #Stream mode
    def startStream(self, settings):
        # For webcam, streaming is essentially the same as regular mode
        # The camera is already continuously capturing
        self.start(settings)
        logger.info("Webcam streaming started")
        
    def stop(self):
        """Clean up webcam resources"""
        if self._cam is not None:
            self._cam.release()
            self._cam = None
            logger.info("Webcam released")
            
    def __del__(self):
        """Ensure camera is released when object is destroyed"""
        self.stop()