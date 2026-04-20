# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Hardware config
from hwconfig import hwconfig1 as hwconfig

import logging
import time
import os
from typing import Any

import RPi.GPIO as GPIO

from CamStates import InitState
from CamStates import PostState
from CamStates import StreamState
from CamStates.state_names import StateName
from Connectivity import cpuserial
from IO import Display
from IO import Light
from IO import CpuTempMonitor
from IO import DS18B20TempMonitor
from Settings.settings_manager import settings_manager
import json
import os

logger = logging.getLogger("cam.mainloop")

#States: Init. Idle, Post, (ImageStream)

class MainLoop:

    def __init__(self, settings: Any = None, hardware_config: dict[str, Any] | None = None):
        self._settings = settings or settings_manager
        self._hardware_config = hardware_config or hwconfig

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
        self._lastds18b20tempcheck = 0
        
        logger.info("Starting temperature monitor initialization...")
              
        self._cputempmonitor = CpuTempMonitor.CpuTempMonitor()
        self._cputemp = self._cputempmonitor.get_cpu_temperature()
        logger.info("CPU temperature monitor initialized: %s°C", self._cputemp)
        
        # Initialize DS18B20 temperature sensor if configured
        logger.info("Checking DS18B20 configuration...")
        ds18b20_pin = self._hardware_config["Io"].get("ds18b20pin")
        logger.info("DS18B20 pin from config: %s", ds18b20_pin)
        if ds18b20_pin is not None:
            try:
                logger.info("Attempting to initialize DS18B20 on pin %s...", ds18b20_pin)
                self._ds18b20tempmonitor = DS18B20TempMonitor.DS18B20TempMonitor(ds18b20_pin)
                self._ds18b20temp = self._ds18b20tempmonitor.get_temperature()
                logger.info("DS18B20 sensor initialized on pin %s, initial reading: %s", ds18b20_pin, self._ds18b20temp)
            except Exception as e:
                logger.error("Failed to initialize DS18B20 sensor: %s", str(e))
                self._ds18b20tempmonitor = None
                self._ds18b20temp = None
        else:
            logger.info("DS18B20 sensor not configured (pin is None)")
            self._ds18b20tempmonitor = None
            self._ds18b20temp = None

        
        #Setup IO, these settings are NOT configurable from backend but hardware dependent
        self._display = Display.Display(
            self._hardware_config["Io"]["displaycontrolgpio"],
            self._hardware_config["Io"]["displaysize"],
        )
        self._display.startup()
     
        if self._hardware_config["LightBox"]:
            pwm_freq = self._settings.get("LightPwmFreq")
            self._lightbox = Light.Light(GPIO, self._hardware_config["Io"]["lightcontrolgpio"], pwm_freq)
            self._last_light_level = None  # Will be set in initialize()
        else:
            self._last_light_level = None  # No lightbox available
        
        #Setup states
        self._initState = InitState.InitState()
        self._postState = PostState.PostState()
        self._streamState = StreamState.StreamState()
        
        self.states = {
            StateName.INIT: self._initState,
            StateName.STREAM: self._streamState,
            StateName.POST: self._postState,
        }

    def initialize(self):
        logger.info("Mainloop initialize")
        if self._hardware_config["LightBox"]:
            light = self._settings.get("Light")
            self._lightbox.start(light)
            self._last_light_level = light  # Track current light level for dynamic updates
            logger.info("Lightbox started with %s%%", light)
        
        # Check Mode setting to determine initial state
        mode = self._settings.get("Mode", "Cam")
        logger.info(f"Mode setting: {mode} - determining initial state")
        
        if mode == "Stream":
            logger.info("Starting in StreamState")
            self.set_state(StateName.STREAM)
        else:
            logger.info("Starting in InitState (camera mode)")
            self.set_state(StateName.INIT)
        
    def update(self):
        # Check for settings reload requests from web interface.
        self._check_settings_reload_request()
        
        #TODO: Check temperatures and other 'house-keeping'

        # Check CPU temperature
        if time.time() - self._lasttempcheck > self._settings.get("CheckCpuTemp"):
            temp_reading = self._cputempmonitor.get_cpu_temperature()
            if temp_reading is not None:
                self._cputemp = temp_reading
                logger.debug("Current CPU-temperature: %s", str(self._cputemp))
                if self._cputemp > self._settings.get("Limits.maxcputemp"):
                    logger.error("Critical CPU-temperature: %s", str(self._cputemp))
                    logger.error("Will halt system for 5 minutes to cool off")
                    time.sleep(300)
                    logger.info("CPU-temperature after cool-off is now: %s", str(self._cputempmonitor.get_cpu_temperature()))
            else:
                logger.warning("Failed to read CPU temperature")
            self._lasttempcheck = time.time()
        
        # Check DS18B20 temperature every 60 seconds
        if self._ds18b20tempmonitor is not None and time.time() - self._lastds18b20tempcheck > 60:
            temp = self._ds18b20tempmonitor.get_temperature()
            if temp is not None:
                self._ds18b20temp = temp
                logger.info("DS18B20 temperature: %.1f°C", temp)
            else:
                logger.warning("Failed to read DS18B20 temperature")
            self._lastds18b20tempcheck = time.time()
            
        # Write runtime status for web interface (every update cycle for timely GUI updates)
        self._update_runtime_status()
        
        #Finally, update the current state logic..                  
        self._currentstate.update(self)      

    def _update_runtime_status(self):
        """Write current runtime status to file for web interface"""
        try:
            status_data = {
                'timestamp': time.time(),
                'cpu_temperature': self._cputemp if self._cputemp is not None else None,
                'ds18b20_temperature': self._ds18b20temp,
                'ds18b20_available': self._ds18b20tempmonitor is not None
            }
            
            status_file = "/tmp/cam_runtime_status.json"
            # Write to temporary file first, then rename for atomic operation
            temp_file = status_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(status_data, f)
            os.rename(temp_file, status_file)
                
        except Exception as e:
            logger.debug("Failed to write runtime status: %s", str(e))      

    def _check_settings_reload_request(self):
        """Check for settings reload requests from web interface."""
        try:
            reload_file = "/tmp/cam_reload_settings.txt"
            if not os.path.exists(reload_file):
                return

            with open(reload_file, 'r') as f:
                reload_type = f.read().strip()

            # Remove request file immediately to avoid repeated processing.
            os.remove(reload_file)

            logger.info("Settings reload requested: %s", reload_type)

            if reload_type == "reload_settings":
                self._settings.load_user_settings()
                
                # Update light PWM duty cycle if Light setting changed
                if self._hardware_config["LightBox"]:
                    current_light = self._settings.get("Light")
                    if hasattr(self, '_last_light_level') and current_light != self._last_light_level:
                        self._lightbox.set_duty(current_light)
                        logger.info("Light duty cycle updated from %s%% to %s%%", self._last_light_level, current_light)
                        self._last_light_level = current_light
                
                desired_mode = str(self._settings.get("Mode", "Cam")).strip().lower()
                current_is_stream = (self._currentstate == self._streamState)

                # Switch state if requested mode differs from current active state.
                if desired_mode == "stream" and not current_is_stream:
                    logger.info("Applying mode switch to StreamState")
                    self.set_state(StateName.STREAM)
                    return
                if desired_mode != "stream" and current_is_stream:
                    logger.info("Applying mode switch to PostState")
                    # Skip init-state on live mode switch and go straight to photo posting state.
                    self.set_state(StateName.POST)
                    return

                # Mode maps to current state: reinitialize current state with updated settings.
                if hasattr(self._currentstate, 'cleanup'):
                    try:
                        self._currentstate.cleanup()
                    except Exception as e:
                        logger.warning("Cleanup failed for current state: %s", e)

                settings_dict = dict(self._settings.get_dict())
                settings_dict.update(self._hardware_config)
                self._currentstate.initialize(settings_dict)
                logger.info("Settings reloaded successfully in current state")

            elif reload_type == "restart_service":
                logger.info("Full service restart requested")
                os.system("sudo systemctl restart camcontroller.service")
            else:
                logger.warning("Unknown reload type: %s", reload_type)
        except Exception as e:
            logger.error("Error processing settings reload request: %s", e)

 
    def set_state(self, state_name: StateName | str):
        if isinstance(state_name, str):
            state_name = StateName(state_name)

        logger.info("State changed to: %s", state_name.value)
        previous_state = getattr(self, "_currentstate", None)

        # Stop/cleanup previous state resources before switching.
        if previous_state is not None:
            if hasattr(previous_state, 'stop_streaming'):
                try:
                    previous_state.stop_streaming()
                except Exception as e:
                    logger.warning("Failed to stop previous streaming state cleanly: %s", e)
            elif hasattr(previous_state, 'cleanup'):
                try:
                    previous_state.cleanup()
                except Exception as e:
                    logger.warning("Failed to cleanup previous state cleanly: %s", e)

        self._currentstate = self.states[state_name]
        
        # Merge hardware config with settings manager data
        settings_dict = dict(self._settings.get_dict())  # Convert SettingsDict to regular dict
        settings_dict.update(self._hardware_config)  # Add hardware configuration to settings
        
        self._currentstate.initialize(settings_dict)


    def stop(self):
        logger.info("Mainloop stopped")
        self._display.off()
        if self._hardware_config["LightBox"]:
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