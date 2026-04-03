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
from Settings.settings_manager import settings_manager
# Import vision pipeline components
from Vision.pipeline.ImageProcessor import ImageProcessor
from Vision.pipeline.processors.CropProcessor import CropProcessor
from Vision.pipeline.processors.MotionDetectionProcessor import MotionDetectionProcessor

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
        
        # Initialize vision pipeline
        self._image_processor = ImageProcessor()
        
        # Configure crop processor if enabled
        if settings_manager.get("Cam.crop"):
            crop_processor = CropProcessor()
            crop_settings = {
                'enabled': True,
                'top_left': settings_manager.get("Cam.crop_topleft"),
                'bottom_right': settings_manager.get("Cam.crop_bottomright"),
                'validate_coordinates': True
            }
            crop_processor.initialize(crop_settings)
            self._image_processor.add_processor(crop_processor)
            logger.info("Crop processor added to pipeline")
        
        # Configure motion detection processor if enabled
        if settings_manager.get("Cam.MotionDetector.active"):
            motion_processor = MotionDetectionProcessor()
            motion_settings = {
                'enabled': True,
                'motion_threshold': settings_manager.get("Cam.MotionDetector.motioncount"),
                'history': settings_manager.get("Cam.MotionDetector.history"),
                'detect_motion_areas': True,
                'min_motion_area': 100
            }
            motion_processor.initialize(motion_settings)
            self._image_processor.add_processor(motion_processor)
            logger.info("Motion detection processor added to pipeline")
        
        #create the publishers using the settings from the config ["Cam"]["publishers"]
        self._publishers = []
        self._save_metadata_json = bool(settings_manager.get("Cam.save_metadata_json"))
        logger.info(f"Save metadata json enabled: {self._save_metadata_json}")
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
        
        logger.info(f"Vision pipeline configured with {len(self._image_processor)} processors")
        return

    def update(self, context):        
        #Don't care about motion detection right now...
        #TODO: add support for schedule
        if time.time() - self._lastsent > settings_manager.get("Cam.timeslot"):     
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
                    # Process image through vision pipeline
                    processed_image, enriched_metadata = self._image_processor.process(
                        self._cam._currentimg, 
                        self._cam._currentMetaData
                    )
                    
                    # Use processed image for encoding
                    currentImage = processed_image
                    
                    # Log processing results
                    if 'processors' in enriched_metadata:
                        for processor_name, processor_data in enriched_metadata['processors'].items():
                            if 'crop_applied' in processor_data and processor_data['crop_applied']:
                                logger.debug(f"Image cropped by {processor_name}")
                            if 'motion_analysis' in processor_data:
                                motion_info = processor_data['motion_analysis']
                                logger.debug(f"Motion detection: {motion_info['motion_detected']} ({motion_info['changed_pixels']} pixels)")
                    
                    # Encode and publish the processed image
                    try:
                        success, jpgimagedata = cv2.imencode(".jpg", currentImage)
                        if success:        
                            # Merge camera metadata with processing metadata
                            final_metadata = self._cam._currentMetaData.copy() if self._cam._currentMetaData else {}
                            if enriched_metadata:
                                final_metadata.update(enriched_metadata)
                            
                            # Publish to all configured publishers
                            for publisher in self._publishers:
                                publisher.publish(jpgimagedata, final_metadata, self._save_metadata_json)
                                logger.debug("Posted image-data to " + type(publisher).__name__)

                        else:
                            logger.error ("Open-cv imencode failed", exc_info=True)     
                    except Exception as e:
                        logger.error(f"Open-cv imencode failed. Cam will try to continue. Exception: {e}", exc_info=True)
                else:
                    logger.error("currentImage is None, skipping processing and upload.")
            except:                
                logger.warning ("PostState update catched an exception but will continue. %s" % str(sys.exc_info()))
            finally:
                self._lastsent = time.time()
                context._display.off()
        return
    
   
    def cleanup(self):
        """Clean up resources for settings reload"""
        logger.info("PostState cleanup for settings reload...")
        try:
            # Temporarily stop the camera for settings reload
            if hasattr(self, '_cam') and self._cam:
                logger.info("Stopping camera for settings reload")
                self._cam.stop()
        except Exception as e:
            logger.error(f"Error during PostState cleanup: {e}")

    def dispose(self):
        #self._cam.
        logger.debug ("PostState resources disposed..")
        #TODO: dispose resources correctly...