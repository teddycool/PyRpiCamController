#Default settings and hw config
from camconfig import defaultsettings
from camconfig import hwconfig

import time
import os
from Connectivity import cpuserial
from IO import Display
from IO import Button
from IO import Light
from IO import Tempmonitor
from CamStates import InitState
from CamStates import PostState
from CamStates import StreamState

import RPi.GPIO as GPIO
from Connectivity import Settings
from camconfig import defaultsettings
import time

import logging
logger = logging.getLogger("cam.mainloop")

#States: Init. Idle, Post, (ImageStream)

class MainLoop(object):

    def __init__(self):

        #TODO: add and check settings for IO enabled
        GPIO.setmode(GPIO.BCM)
        self.mycpuserial = cpuserial.getserial()
        self._settingsMngr = Settings.Settings(defaultsettings)
        logger.info("My serial is : " + self.mycpuserial)

        self._lastconfigcheck = 0
        self._lasttempcheck = 0      
              
        self._cputempmonitor = Tempmonitor.TempMonitor()
        self._cputemp = self._cputempmonitor.get_cpu_temperature()

        
        #Setup IO, these settings are NOT configurable from backend but hardware (camera) dependent
        self._display = Display.Display(hwconfig["Io"]["displaycontrolgpio"], hwconfig["Io"]["displaysize"])   
        self._display.no_internet()     
     
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
        self._initState.initialize(self._settingsMngr.curSettings)
        self._currentstate = self._initState
        if (hwconfig["LightBox"]):
            light =self._settingsMngr.curSettings["Light"]
            self._lightbox.start(light)
            logger.info("Lightbox started with " + str(light) + "%")  
        
    def update(self):
        #TODO:  Check for new settings on server
        # if time.time() - self._lastconfigcheck > self._settingsMngr.curSettings["CheckNewSettings"]: 
        #     if self._settingsMngr.checkForUpdates(self._mycpuserial):
        #         #There are new settings available, needs a reboot to start everything with new settings value
        #         os.system("sudo reboot")
        #     self._lastconfigcheck = time.time()  

        #TODO: Check temperatures and other 'house-keeping'

        if time.time() - self._lasttempcheck > self._settingsMngr.curSettings["CheckCpuTemp"]:
            self._cputemp=self._cputempmonitor.get_cpu_temperature()
            self._lasttempcheck = time.time()
            logger.debug("Current CPU-temperature: " + str(self._cputemp))
            if self._cputemp > self._settingsMngr.curSettings["Limits"]["maxcputemp"]:
                logger.error("Critical CPU-temperature: " + str(self._cputemp))
                logger.error("Will halt system for 5 minutes to cool off")
                time.sleep(300)
                logger.info("CPU-temperature after cool-off is now: " + str(self._cputempmonitor.get_cpu_temperature()))
            else:   
                if self._cputemp > self._settingsMngr.curSettings["Limits"]["wcputemp"]:
                    logger.warning("High CPU-temperature: " + str(self._cputemp))
        #Finally, update the current state logic..                  
        self._currentstate.update(self)      

 
    def setState(self, statename):
        logger.info("State changed to: " + statename)
        #TODO: dispose resources from previous state
        self._currentstate = self.states[statename]
        self._currentstate.initialize(self._settingsMngr.curSettings)

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