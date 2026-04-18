# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import os
import time
from Connectivity import WiFi
from CamStates import BaseState
from CamStates.state_names import StateName
# Add project root to path for settings manager
import sys
from Settings.settings_manager import settings_manager

import logging
logger = logging.getLogger("cam.state.initstate")

class InitState(BaseState.BaseState):
    def __init__(self):
        super(InitState, self).__init__()
        return

    def initialize(self, settings):
        #Init clockinit state
        logger.info("InitState initialize..")        
        self._lastconcheck = 0
        self._wifi = WiFi.WiFi()
        return

    def update(self, context):
        logger.info ("InitState update..")
        if time.time() - self._lastconcheck > 1: 
            self._lastconcheck = time.time()
            if (self._wifi.connection_check()):
                context._display.wifi_connected()
                logger.info ("Connected")
                settings_store = getattr(context, "_settings", settings_manager)
                if settings_store.get("Mode") == "Cam":
                    context.set_state(StateName.POST)
                if settings_store.get("Mode") == "Stream":
                    context.set_state(StateName.STREAM)
                #TODO: add ota state ?                
        else:
            logger.info ("Not connected yet...")
            context._display.no_internet()
        return
        
  