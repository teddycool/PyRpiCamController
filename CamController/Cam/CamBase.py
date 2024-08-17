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

    def iResSupported(self, res): #Check if res (x,y) is supported by camera for images
        return self._supportedImagesResolutions.count(res)==1
    
    def vResSupported(self, res): #Check if res (x,y) is supported by camera for video
        return self._supportedVideoResolutions.count(res)==1

    def startStreaming(self):   #Start 'recording' to io-buffer
        raise NotImplementedError




def getCam(camtype):
    if (camtype == "PiCam3"):
        from Cam import  PiCam3
        cam = PiCam3.PiCam3()
        return cam
    if (camtype == "PiCamHQ"):
        from Cam import PiCamHQ
        return PiCamHQ.PiCamHQ()
    