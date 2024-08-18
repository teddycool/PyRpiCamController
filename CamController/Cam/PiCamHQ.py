from Cam import CamBase
from picamera2 import Picamera2, Preview
import libcamera
import requests
import time
import logging
logger = logging.getLogger("cam.PiCamHQ")
import json
import sys

#How to handle different types/generations of cams? Like picam1 and picam2 with different capabilities

class PiCamHQ(CamBase.CamBase):
    def __init__(self):
        super(PiCamHQ, self).__init__()
        self._supportedImagesResolutions= [(4608,2592)]
        return
    
 #Cam mode   
    def start(self, settings):
        res = (settings["Cam"]["width"], settings["Cam"]["height"])

        if not self.iResSupported(res):
            logger.warning("Cam resolution " + str(res) + " requested in config, but not supported!")            
            logger.info("Setting first valid res from list " + str(self._supportedImagesResolutions) )
            res = self._supportedImagesResolutions[0]

        self._cam = Picamera2()
        self._camconf =  self._cam.create_still_configuration({"format": "RGB888", "size": res})
        logger.info("Cam-config: " +  self._camconf["main"])
        self._cam.configure(self._camconf)
        self._cam.start(show_preview=False)
        self._cam.set_controls({"AwbMode": libcamera.controls.AwbModeEnum.Auto}) 
        self._cam.set_controls({"AeEnable": True}) 
        self._cam.set_controls({"AeExposureMode": libcamera.controls.AeExposureModeEnum.Short}) 
    
    def initialize(self, settings):
        #Can't change cam settings on the fly, yet...
        #self.update() 
        pass
        
    def update(self):
        try:
            request = self._cam.capture_request()
            self._currentimg = request.make_array("main")
          #  self._currentimg = self._cam.capture_array("main")    #How to avoid lock-up here? 
            self._currentMetaData = request.get_metadata()
            request.release()
            logger.debug("Current image buffer updated")   
            logger.debug("Current metadata: " + json.dumps(self._currentMetaData))
        except:
            logger.warning("Failed to update image buffer %s" % sys.exc_info())  
        
#Stream mode

    def startStream(self, settings):
         self._cam = Picamera2()
    