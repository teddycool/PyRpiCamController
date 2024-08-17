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
                try:
                    success, ajpegnumpy = cv2.imencode('.jpg', self._cam._currentimg)
                    if success:
                        data = ajpegnumpy.tostring()
                        files = {'media': data}
                        url = self._url + '?cpu=' + context.mycpuserial + '&meta=' + json.dumps(self._cam._currentMetaData)
                        r = requests.post(url, files=files)
                        logger.debug("Posting image-data to " + url)
                        logger.debug("Posting received http-status: " + str(r.status_code))
                    else:
                        logger.warning ("Open-cv imencode failed")     
                except:
                    logger.error ("Open-cv imencode to jpegnumpy failed. Cam will try to continue. %s",  exc_info=1)    
            except:                
                logger.warning ("PostState update catched an exception but will continue. %s", exc_info=1)
            finally:
                self._lastsent = time.time()
                context._display.off()
        return
    
   
    def dispose(self):
        #self._cam.
        logger.debug ("PostState resources disposed..")
        #TODO: dispose resources correctly...