# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import time
from Connectivity import WiFi
from CamStates import BaseState
from CamStates.state_names import StateName
import logging
logger = logging.getLogger("cam.state.initstate")

class InitState(BaseState.BaseState):
    def __init__(self):
        super(InitState, self).__init__()
        self._last_connection_check = None
        self._last_connection_result = None
        return

    def initialize(self, settings):
        super().initialize(settings)
        logger.info("InitState initialize..")        
        self._lastconcheck = 0
        self._last_connection_check = None
        self._last_connection_result = None
        self._wifi = WiFi.WiFi()
        return

    def update(self, context):
        logger.info ("InitState update..")
        if time.time() - self._lastconcheck > 1: 
            self._lastconcheck = time.time()
            self._last_connection_check = self._lastconcheck
            self._last_connection_result = bool(self._wifi.connection_check())
            if self._last_connection_result:
                context._display.wifi_connected()
                logger.info ("Connected")
                if self._settings.get("Mode") == "Cam":
                    context.set_state(StateName.POST)
                if self._settings.get("Mode") == "Stream":
                    context.set_state(StateName.STREAM)
                #TODO: add ota state ?                
        else:
            logger.info ("Not connected yet...")
            context._display.no_internet()
        return

    def get_metrics(self):
        """Return boot/network readiness metrics."""
        return {
            "wifi_connected": self._last_connection_result,
            "last_connection_check": self._last_connection_check,
        }

    def cleanup(self):
        """Release state resources."""
        self._wifi = None

    def dispose(self):
        """Release state resources during shutdown."""
        self.cleanup()
