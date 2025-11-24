# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import MainLoop
import time
import os
import sys
import logging
import logging.handlers
from Connectivity import cpuserial
import json
# Import the new settings manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Settings.settings_manager import settings_manager

# TODO: check for OTA at start, if enabled start with new thread, close current and restart after install

#if(ota):
#    os.system("python /home/pi/ota/installota.py &")
 
mycpuserial = cpuserial.getserial().lstrip("0")

# TODO: get all settings from server at start...

import logging
loglevels = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR, "critical": logging.CRITICAL}
try:
    loglevel = loglevels[settings_manager.get("LogLevel").lower()]
except:
    loglevel = logging.DEBUG

old_factory = logging.getLogRecordFactory()

#Adding cpuid to the logging records
def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.cpuid = mycpuserial
    return record
logging.setLogRecordFactory(record_factory)


logger = logging.getLogger("cam")
logger.setLevel(loglevel)


#Settings formatters for log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
jsonformatter = logging.Formatter(json.dumps({
    'time': '%(asctime)s',
    'logname': '%(name)s',
    'logLevel': '%(levelname)s',
    'message': '%(message)s'
}))

#Default, always log to the console
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)

if settings_manager.get("LogToServer"):
    # Use secure logging if API key is configured
    log_api_key = settings_manager.get("LogApiKey")
    if log_api_key:
        from LoggingSecure import LoggingSecureHandler
        secure_handler = LoggingSecureHandler(
            host=settings_manager.get("LogHost"),
            url=settings_manager.get("LogUrl"),
            api_key=log_api_key
        )
        secure_handler.setFormatter(jsonformatter)
        logger.addHandler(secure_handler)
    else:
        httph = logging.handlers.HTTPHandler(
            host=settings_manager.get("LogHost"), 
            url=settings_manager.get("LogUrl"), 
            method="GET", 
            secure=False
        )
        logger.addHandler(httph)

if settings_manager.get("LogToFile"):
    fh = logging.handlers.RotatingFileHandler(
        settings_manager.get("LogFilePath"),
        maxBytes=settings_manager.get("LogFileSize"), 
        backupCount=settings_manager.get("LogFileBuCount")
    )
    fh.setFormatter(jsonformatter)
    logger.addHandler(fh)


class Main(object):
    def __init__(self):
        logger.info("PyCam is starting...")
        logger.info("MainObject init")        #
        self._mainLoop=MainLoop.MainLoop()
       

    def run(self):        
        logger.info("Starting mainloop initialize")
        self._mainLoop.initialize()
        running = True
        logger.info ("Starting mainloop update")
        while running:
            try:
                self._mainLoop.update()
                time.sleep(0.5)
            except (KeyboardInterrupt):
                logger.info ("User stopped the mainloop")
                self._mainLoop.stop()
                running = False
            except :
                logger.exception("Mainloop caught an exception but will continue")
        logger.info("PyCam has stopped")

    def __del__(self):
        logger.info("Mainloop destructor")
        




if __name__ == "__main__":
    cd=Main()
    cd.run()

