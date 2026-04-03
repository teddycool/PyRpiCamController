# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Parent-class for all publishers


class PublisherBase(object):

    def __init__(self):
        raise NotImplementedError 
    
    def __del__(self):
        raise NotImplementedError
    
    def initialize(self, settings):  #Init publisher with current settings from config
        raise NotImplementedError   
    
    def publish(self, jpgimagedata, metadata, save_metadata_json=False): #Publish the image and metadata 
        raise NotImplementedError
