# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Hardware config
from hwconfig import hwconfig1 as hwconfig

import time
import os
from Connectivity import cpuserial
from IO import Display
#from IO import Button
from IO import Light
from IO import Tempmonitor
from CamStates import InitState
from CamStates import PostState
from CamStates import StreamState

import RPi.GPIO as GPIO
from hwconfig import hwconfig1 as hwconfig
import time

# Add project root to path for settings manager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Settings.settings_manager import settings_manager

import logging
logger = logging.getLogger("cam.mainloop")

#States: Init. Idle, Post, (ImageStream)

class MainLoop(object):

    def __init__(self):

        #TODO: add and check settings for IO enabled
        GPIO.setmode(GPIO.BCM)
        self.mycpuserial = cpuserial.getserial()
        logger.info("My serial is : " + self.mycpuserial)

        self._lastconfigcheck = 0
        self._lasttempcheck = 0      
              
        self._cputempmonitor = Tempmonitor.TempMonitor()
        self._cputemp = self._cputempmonitor.get_cpu_temperature()

        
        #Setup IO, these settings are NOT configurable from backend but hardware (camera) dependent
        self._display = Display.Display(hwconfig["Io"]["displaycontrolgpio"], hwconfig["Io"]["displaysize"])   
        self._display.startup()     
     
        if (hwconfig["LightBox"]):
            self._lightbox = Light.Light(GPIO,hwconfig["Io"]["lightcontrolgpio"])        
        
        #Setup states
        self._initState = InitState.InitState()
        self._postState = PostState.PostState()
   #     self._streamState = StreamState.StreamState()
        
        self.states = {"InitState": self._initState, 
        #               "StreamState": self._streamState,
                       "PostState": self._postState}              

    def initialize(self):
        logger.info("Mainloop initialize")      
        if (hwconfig["LightBox"]):
            light = settings_manager.get("Light")
            self._lightbox.start(light)
            logger.info("Lightbox started with " + str(light) + "%")  
        self.setState("InitState")
        
    def update(self):
        #TODO:  Check for new settings on server
        # if time.time() - self._lastconfigcheck > self._settingsMngr.curSettings["CheckNewSettings"]: 
        #     if self._settingsMngr.checkForUpdates(self._mycpuserial):
        #         #There are new settings available, needs a reboot to start everything with new settings value
        #         os.system("sudo reboot")
        #     self._lastconfigcheck = time.time()  

        #TODO: Check temperatures and other 'house-keeping'

        if time.time() - self._lasttempcheck > settings_manager.get("CheckCpuTemp"):
            self._cputemp=self._cputempmonitor.get_cpu_temperature()
            self._lasttempcheck = time.time()
            logger.debug("Current CPU-temperature: " + str(self._cputemp))
            if self._cputemp > settings_manager.get("Limits.maxcputemp"):
                logger.error("Critical CPU-temperature: " + str(self._cputemp))
                logger.error("Will halt system for 5 minutes to cool off")
                time.sleep(300)
                logger.info("CPU-temperature after cool-off is now: " + str(self._cputempmonitor.get_cpu_temperature()))
            else:   
                if self._cputemp > settings_manager.get("Limits.wcputemp"):
                    logger.warning("High CPU-temperature: " + str(self._cputemp))
        #Finally, update the current state logic..                  
        self._currentstate.update(self)      

 
    def setState(self, statename):
        logger.info("State changed to: " + statename)
        #TODO: dispose resources from previous state
        self._currentstate = self.states[statename]
        self._currentstate.initialize(settings_manager.get_dict())

    def stop(self):
        logger.info("Mainloop stopped")
        self._display.off()
        if (hwconfig["LightBox"]):
            logger.info("Lightbox stopped")
            self._lightbox.stop()



if __name__ == '__main__':
    print ("Testcode for MainLoop")
    ml = MainLoop()
    ml.initialize()
    try:
        while(True):
            ml.update()
            time.sleep(0.5)
    except KeyboardInterrupt:
        ml.stop()
        print("Testcode ended...")
    except:
        pass