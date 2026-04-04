# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from Cam import CamBase
import cv2
import time
import logging
import json
import datetime

logger = logging.getLogger("cam.WebCam")

class WebCam(CamBase.CamBase):
    def __init__(self):
        super().__init__()
        self._supported_image_resolutions = [(1920, 1080), (1280, 720), (640, 480)]
        self._supported_video_resolutions = [(1920, 1080), (1280, 720), (640, 480)]
        self._cam = None
        self._device_index = 0  # Default webcam device index
    
    #Cam mode   
    def start(self, settings):
        res = tuple(settings["Cam"]["resolution"])

        if not self.is_image_resolution_supported(res):
            logger.warning("Cam resolution %s requested in config, but not supported!", str(res))
            logger.info("Setting first valid res from list %s", str(self._supported_image_resolutions))
            res = self._supported_image_resolutions[0]

        # Initialize the webcam
        self._cam = cv2.VideoCapture(self._device_index)
        
        if not self._cam.isOpened():
            logger.error("Could not open webcam device %s", str(self._device_index))
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
        logger.info("Webcam initialized with resolution: %sx%s", actual_width, actual_height)
        
        # Warm up the camera
        for _ in range(5):
            self._cam.read()
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
                self._current_image = None
                self._current_metadata = None
                return
                
            ret, frame = self._cam.read()
            
            if not ret:
                logger.warning("Failed to capture frame from webcam")
                self._current_image = None
                self._current_metadata = None
                return
                
            # Convert from BGR (OpenCV default) to RGB 
            self._current_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create metadata similar to Pi camera
            self._current_metadata = {
                "timestamp": datetime.datetime.now().isoformat(),
                "ExposureTime": int(self._cam.get(cv2.CAP_PROP_EXPOSURE)) if self._cam.get(cv2.CAP_PROP_EXPOSURE) != -1 else 0,
                "FrameWidth": int(self._cam.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "FrameHeight": int(self._cam.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "Brightness": int(self._cam.get(cv2.CAP_PROP_BRIGHTNESS)) if self._cam.get(cv2.CAP_PROP_BRIGHTNESS) != -1 else 0,
                "CameraType": "WebCam"
            }
             
            logger.debug("Current image size: %s", str(self._current_image.size))
            logger.debug("Current image buffer updated")   
            logger.debug("Current metadata: %s", json.dumps(self._current_metadata))
            
        except Exception as e:
            logger.warning("Failed to update image buffer: %s", str(e))
            self._current_image = None
            self._current_metadata = None
        
    #Stream mode
    def start_stream(self, settings=None):
        if settings is None:
            settings = {}
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