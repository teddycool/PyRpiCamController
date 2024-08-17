from Cam import CamBase
from picamera2 import Picamera2, Preview
import libcamera
import requests
import time
import logging
logger = logging.getLogger("cam.PiCam3")

#How to handle different types/generations of cams? Like picam1 and picam2 with different capabilities

class PiCamHQ(CamBase.CamBase):
    def __init__(self):
        super(PiCamHQ, self).__init__()
        return
    
 #Cam mode   
    def start(self, settings):
        self._cam = Picamera2()
        self._camconf =  self._cam.create_still_configuration({"format": "RGB888", "size": (settings["Cam"]["width"], settings["Cam"]["height"])})
        logger.info("Cam-config %s", self._camconf["main"])
        self._cam.configure(self._camconf)
        self._cam.start(show_preview=False)
        self._cam.set_controls({"AfMode": libcamera.controls.AfModeEnum.Continuous}) 
        self._cam.set_controls({"AwbMode": libcamera.controls.AwbModeEnum.Auto}) 
        self._cam.set_controls({"AeEnable": True}) 
        self._cam.set_controls({"AeExposureMode": libcamera.controls.AeExposureModeEnum.Short}) 
    
    def initialize(self, settings):
        #Can't change cam settings on the fly, yet...
        #self.update() 
        pass
        
    def update(self):
        try:
            success = self._cam.autofocus_cycle()
            if not success:
                logger.info("Current image might be blurry. Autofocus cycle failed.")  
            self._currentimg = self._cam.switch_mode_and_capture_array(self._camconf, "main")    
            logger.debug("Current image updated in memory")   
        except:
            logger.warning("Failed to update current image", exc_info=1)  
        
#Stream mode

    def startStream(self, settings):
         self._cam = Picamera2()
    