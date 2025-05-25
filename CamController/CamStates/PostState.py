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
            currentImage = None
            try:       
                context._display.image_post()
                self._cam.update()
                if context._settingsMngr.curSettings["Cam"]["crop"] == True:
                    logger.debug("Image will be cropped before sending")
                    logger.debug("Crop settings: " + str(context._settingsMngr.curSettings["Cam"]["ctopleft"]) + " " + str(context._settingsMngr.curSettings["Cam"]["cbottomright"]))         
                    x1, y1 = context._settingsMngr.curSettings["Cam"]["ctopleft"]
                    x2, y2 = context._settingsMngr.curSettings["Cam"]["cbottomright"]
                    # Validate crop coordinates
                    img = self._cam._currentimg
                    logger.debug(f"x1={x1}, y1={y1}, x2={x2}, y2={y2}, img.shape={img.shape if img is not None else None}")
                    if img is not None and 0 <= x1 < x2 <= img.shape[1] and 0 <= y1 < y2 <= img.shape[0]:
                        currentImage = img[y1:y2, x1:x2]
                    else:
                        logger.error("Invalid crop coordinates or image is None. Sending full image instead.")
                        currentImage = img
                else:
                    logger.debug("Image will not be cropped before sending")
                    currentImage = self._cam._currentimg

                # Check if currentImage is valid before encoding
                if currentImage is not None and currentImage.size > 0:
                    format = ".jpg"
                    try:
                        success, aimgnumpy = cv2.imencode(format, currentImage)
                        if success:                        
                            data = aimgnumpy.tobytes()
                            files = {'media': data}
                            url = self._url + '?cpu=' + context.mycpuserial + '&meta=' + json.dumps(self._cam._currentMetaData)
                            r = requests.post(url, files=files)
                            logger.debug("Posted image-data to " + url)                        
                            logger.debug("Received http-status: " + str(r.status_code))
                        else:
                            logger.error ("Open-cv imencode failed", exc_info=True)     
                    except Exception as e:
                        logger.error("Open-cv imencode failed. Cam will try to continue.", exc_info=True)
                else:
                    logger.error("currentImage is None or empty, skipping encoding and upload.")
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