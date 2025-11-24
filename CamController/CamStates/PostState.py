# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import os
import time
from CamStates import BaseState
import time
from Cam import CamBase
import requests
import cv2
#from Vision import MotionDetector
import logging
from hwconfig import hwconfig1 as hwconfig
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
        self._cam = CamBase.getCam(settings["CamChip"])
        logger.debug ("CamType: " + str(self._cam))
        self._cam.start(settings)
        #create the publishers using the settings from the config ["Cam"]["publishers"]
        self._publishers = []
        for pub_type, pub_settings in settings["Cam"]["publishers"].items():
            if pub_type == "url" and pub_settings.get("publish", True):
                from Publishers.HttpPublisher import HttpPublisher
                publisher = HttpPublisher()
                publisher.initialize(settings)
                self._publishers.append(publisher)
            elif pub_type == "file" and pub_settings.get("publish", True):
                from Publishers.FilePublisher import FilePublisher
                publisher = FilePublisher()
                publisher.initialize(settings)
                self._publishers.append(publisher)
            else:
                logger.warning(f"Unsupported or disabled publisher type: {pub_type}")
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
            camupdated = False
            try:       
                context._display.image_post()
                self._cam.update()
                camupdated = True   
            except Exception as e:
                logger.error(f"PostState update failed. Cam will try to continue. Exception: {e}", exc_info=True)

            try:
                if  camupdated:  #Update of image buffer was successful                    
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
                            logger.warning("Invalid crop coordinates or image is None. Sending full image instead.")
                            currentImage = img
                    else:
                        logger.debug("Image will not be cropped before sending")
                        currentImage = self._cam._currentimg
                    try:
                        success, jpgimagedata = cv2.imencode(".jpg", currentImage)
                        if success:        
                            for publisher in self._publishers:
                                publisher.publish(jpgimagedata, self._cam._currentMetaData)      
                                logger.debug("Posted image-data to " + type(publisher).__name__)

                        else:
                            logger.error ("Open-cv imencode failed", exc_info=True)     
                    except Exception as e:
                        logger.error(f"Open-cv imencode failed. Cam will try to continue. Exception: {e}", exc_info=True)
                else:
                            logger.error("currentImage is  None, skipping encoding and upload.")
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