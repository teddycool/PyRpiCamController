# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'
#REFs: 
# https://w1.fi/cgit/hostap/plain/wpa_supplicant/README-WPS
#https://unix.stackexchange.com/questions/238180/execute-shell-commands-in-python

import os
import time
from urllib.request import urlopen

import logging
logger = logging.getLogger("cam.connectivity.wifi")

class WiFi(object):

    _testurl = "http://www.google.com"

    def __init__(self):
        logger.debug ("Init WiFi management")


    def ConnectionCheck(self):
        logger.debug (" Checking connection....")
        connected = False
        try:
            turl = urlopen(self._testurl, timeout=5)
            logger.debug ("Responsecode: " + str(turl.status))
            connected = True
        except:
            connected = False
        return connected
        


if __name__ == '__main__':
    print ("Testcode for WiFi")
    wifi=WiFi()
    print (wifi.ConnectionCheck())