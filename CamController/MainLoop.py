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
        self._streamState = StreamState.StreamState()
        
        self.states = {"InitState": self._initState, 
                       "StreamState": self._streamState,
                       "PostState": self._postState}              

    def initialize(self):
        logger.info("Mainloop initialize")      
        if (hwconfig["LightBox"]):
            light = settings_manager.get("Light")
            self._lightbox.start(light)
            logger.info("Lightbox started with " + str(light) + "%")  
        self.setState("InitState")
        
    def update(self):
        #TODO:  Check for new settings on server using unified settings system
        # Check for settings reload requests from web interface
        self._check_settings_reload_request()

        # Check for state change requests from web interface
        self._check_state_change_request()

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
        
        # Merge hardware config with settings manager data
        settings_dict = dict(settings_manager.get_dict())  # Convert SettingsDict to regular dict
        settings_dict.update(hwconfig)  # Add hardware configuration to settings
        
        self._currentstate.initialize(settings_dict)

    def _check_settings_reload_request(self):
        """Check for settings reload requests from web interface"""
        try:
            reload_file = "/tmp/cam_reload_settings.txt"
            if os.path.exists(reload_file):
                with open(reload_file, 'r') as f:
                    reload_type = f.read().strip()
                
                # Remove the request file
                os.remove(reload_file)
                
                logger.info(f"Settings reload requested: {reload_type}")
                
                if reload_type == "restart_service":
                    # Full service restart
                    logger.info("Full service restart requested")
                    os.system("sudo systemctl restart pycam")
                elif reload_type == "reload_settings":
                    # Reload settings without full restart
                    logger.info("Reloading settings...")
                    settings_manager.load_user_settings()
                    
                    # Get current state name to preserve it
                    current_state_name = None
                    for state_name, state_obj in self.states.items():
                        if state_obj == self._currentstate:
                            current_state_name = state_name
                            break
                    
                    logger.info(f"Preserving current state: {current_state_name}")
                    
                    # Re-initialize current state with new settings (preserves current mode)
                    settings_dict = dict(settings_manager.get_dict())
                    settings_dict.update(hwconfig)
                    
                    # If current state has cleanup method, call it first
                    if hasattr(self._currentstate, 'cleanup'):
                        try:
                            self._currentstate.cleanup()
                        except Exception as e:
                            logger.warning(f"Cleanup failed for current state: {e}")
                    
                    # Re-initialize the same state with new settings
                    self._currentstate.initialize(settings_dict)
                    
                    logger.info("Settings reloaded successfully - state preserved")
                else:
                    logger.warning(f"Unknown reload type: {reload_type}")
                    
        except Exception as e:
            logger.error(f"Error processing settings reload request: {e}")
    
    def _check_state_change_request(self):
        """Check for state change requests from web interface"""
        try:
            state_file = "/tmp/cam_state_request.txt"
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    requested_state = f.read().strip()
                
                # Remove the request file
                os.remove(state_file)
                
                # Validate and change state
                if requested_state in self.states:
                    logger.info(f"State change requested via web interface: {requested_state}")
                    self.setState(requested_state)
                else:
                    logger.warning(f"Invalid state requested: {requested_state}")
                    
        except Exception as e:
            logger.error(f"Error checking state change request: {e}")
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