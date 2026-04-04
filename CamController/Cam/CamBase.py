# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Parent-class for all cams
#https://en.wikipedia.org/wiki/State_pattern
import time


class CamBase(object):

    def __init__(self):
        self._currentimg = None  #Must be a numpy array
        self._currentMetaData = None #A Python dictionary
        self._supportedImagesResolutions = [] # like: [(4608,2592)]
        self._supportedVideoResolutions = [] # like: [(800,600)]
        return

    def initialize(self):  #Init camera with current settings from config
        raise NotImplementedError

    def update(self, context): #Update current image (and metadata) with latest frame from cam
        raise NotImplementedError 

    def is_image_resolution_supported(self, res): #Check if res (x,y) is supported by camera for images
        return self._supportedImagesResolutions.count(res)==1
    
    def is_video_resolution_supported(self, res): #Check if res (x,y) is supported by camera for video
        return self._supportedVideoResolutions.count(res)==1

    def start_stream(self, settings=None):   # Start streaming to io-buffer
        raise NotImplementedError




def get_cam(camtype):
    if (camtype == "PiCam2"):
        from Cam import PiCam2
        return PiCam2.PiCam2()
    if (camtype == "PiCam3"):
        from Cam import  PiCam3
        cam = PiCam3.PiCam3()
        return cam
    if (camtype == "PiCamHQ"):
        from Cam import PiCamHQ
        return PiCamHQ.PiCamHQ()
    if (camtype == "WebCam"):
        from Cam import WebCam
        return WebCam.WebCam()
    
    raise ValueError("Unknown camera type: " + str(camtype))