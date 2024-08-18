import os
import time
from CamStates import BaseState
import time
from Cam import CamBase
import requests
import cv2
#from Vision import MotionDetector
import logging
from camconfig import hwconfig
import json
import sys

logger = logging.getLogger("cam.state.poststate")

class PostState(BaseState.BaseState):
    def __init__(self):
        super(PostState, self).__init__()
        return

    def initialize(self, settings):
        logger.debug ("PostState initialize..")
         #Setup Cam
        self._lastsent = 0 #Force first image
        self._cam = CamBase.getCam(hwconfig["CamChip"])
        logger.debug ("CamType: " + str(self._cam))
        self._cam.start(settings)
        self._url = settings["Cam"]["posturl"]   
        
     #   self._md =  MotionDetector.MotionDetector()
     #   self._md.initialize()
        return

    def update(self, context):        
        #Don't care about motion detection right now...
        #TODO: add support for schedule
        if time.time() - self._lastsent > context._settingsMngr.curSettings["Cam"]["timeslot"]:     
            logger.debug ("PostState will try to update and send new image..")
            try:       
                context._display.image_post()
                self._cam.update()
                #We are only handling image-data in memory. NO writing to the sd-card.
                #TODO: for now only jpg files are supported in the backend but this should be a parameter in usersettings
                format = ".jpg"
                try:
                    success, aimgnumpy = cv2.imencode(format, self._cam._currentimg,[int(cv2.IMWRITE_JPEG_QUALITY), 100])
                    if success:
                        data = aimgnumpy.tostring()
                        files = {'media': data}
                        url = self._url + '?cpu=' + context.mycpuserial + '&format=' + format + '&meta=' + json.dumps(self._cam._currentMetaData)
                        r = requests.post(url, files=files)
                        logger.debug("Posted image-data to " + url)                        
                        logger.debug("Received http-status: " + str(r.status_code))
                    else:
                        logger.warning ("Open-cv imencode failed")     
                except:
                    logger.error ("Open-cv imencode to failed. Cam will try to continue. %s" %  str(sys.exc_info()))    
            except:                
                logger.warning ("PostState update catched an exception but will continue. %s" % str(sys.exc_info()))
            finally:
                self._lastsent = time.time()
                context._display.off()
        return
    
   
    def dispose(self):
        #self._cam.
        logger.debug ("PostState resources disposed..")
        #TODO: dispose resources correctly...