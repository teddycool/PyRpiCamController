# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Hardware config
from hwconfig import hwconfig1 as hwconfig

import logging
import time

import RPi.GPIO as GPIO

from CamStates import InitState
from CamStates import PostState
from CamStates import StreamState
from Connectivity import cpuserial
from IO import Display
from IO import Light
from IO import Tempmonitor
from Settings.settings_manager import settings_manager

logger = logging.getLogger("cam.mainloop")

#States: Init. Idle, Post, (ImageStream)

class MainLoop:

    def __init__(self):

        #TODO: add and check settings for IO enabled
        try:
            GPIO.setmode(GPIO.BCM)
            logger.info("GPIO initialized successfully")
        except Exception as e:
            logger.error(f"GPIO initialization failed: {e}")
            # Try to cleanup and retry
            try:
                GPIO.cleanup()
                GPIO.setmode(GPIO.BCM)
                logger.info("GPIO initialized successfully after cleanup")
            except Exception as e2:
                logger.error(f"GPIO initialization failed even after cleanup: {e2}")
                raise
                
        self.mycpuserial = cpuserial.getserial()
        logger.info("My serial is: %s", self.mycpuserial)

        self._lastconfigcheck = 0
        self._lasttempcheck = 0      
              
        self._cputempmonitor = Tempmonitor.TempMonitor()
        self._cputemp = self._cputempmonitor.get_cpu_temperature()

        
        #Setup IO, these settings are NOT configurable from backend but hardware dependent
        self._display = Display.Display(hwconfig["Io"]["displaycontrolgpio"], hwconfig["Io"]["displaysize"])
        self._display.startup()
     
        if (hwconfig["LightBox"]):
            self._lightbox = Light.Light(GPIO, hwconfig["Io"]["lightcontrolgpio"])
        
        #Setup states
        self._initState = InitState.InitState()
        self._postState = PostState.PostState()
        self._streamState = StreamState.StreamState()
        
        self.states = {"InitState": self._initState, 
                       "StreamState": self._streamState,
                       "PostState": self._postState}              

    def initialize(self):
        logger.info("Mainloop initialize")
        if (hwconfig["LightBox"]):
            light = settings_manager.get("Light")
            self._lightbox.start(light)
            logger.info("Lightbox started with %s%%", light)
        
        # Check Mode setting to determine initial state
        mode = settings_manager.get("Mode", "Cam")
        logger.info(f"Mode setting: {mode} - determining initial state")
        
        if mode == "Stream":
            logger.info("Starting in StreamState")
            self.set_state("StreamState")
        else:
            logger.info("Starting in InitState (camera mode)")
            self.set_state("InitState")
        
    def update(self):
        # Settings changes are handled by webapp restart of camcontroller service
        # No runtime settings reload needed - service restart ensures clean initialization
        
        #TODO: Check temperatures and other 'house-keeping'

        if time.time() - self._lasttempcheck > settings_manager.get("CheckCpuTemp"):
            self._cputemp = self._cputempmonitor.get_cpu_temperature()
            self._lasttempcheck = time.time()
            logger.debug("Current CPU-temperature: %s", str(self._cputemp))
            if self._cputemp > settings_manager.get("Limits.maxcputemp"):
                logger.error("Critical CPU-temperature: %s", str(self._cputemp))
                logger.error("Will halt system for 5 minutes to cool off")
                time.sleep(300)
                logger.info("CPU-temperature after cool-off is now: %s", str(self._cputempmonitor.get_cpu_temperature()))
            else:   
                if self._cputemp > settings_manager.get("Limits.wcputemp"):
                    logger.warning("High CPU-temperature: %s", str(self._cputemp))
        #Finally, update the current state logic..                  
        self._currentstate.update(self)      

 
    def set_state(self, statename):
        logger.info("State changed to: %s", statename)
        #TODO: dispose resources from previous state
        self._currentstate = self.states[statename]
        
        # Merge hardware config with settings manager data
        settings_dict = dict(settings_manager.get_dict())  # Convert SettingsDict to regular dict
        settings_dict.update(hwconfig)  # Add hardware configuration to settings
        
        self._currentstate.initialize(settings_dict)


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