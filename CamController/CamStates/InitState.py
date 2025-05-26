import os
import time
from Connectivity import WiFi
from CamStates import BaseState

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
            if (self._wifi.ConnectionCheck()):
                context._display.wifi_connected()
                logger.info ("Connected")
                if context._settingsMngr.curSettings["Mode"] == "Cam":
                    context.setState("PostState")
                if context._settingsMngr.curSettings["Mode"] == "Stream":
                    context.setState("StreamState")
                #TODO: add ota state ?                
        else:
            logger.info ("Not connected yet...")
            context._display.no_internet()
        return
        
  