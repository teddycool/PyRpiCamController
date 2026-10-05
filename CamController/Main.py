# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import os
import sys

# Ensure the project root (parent of CamController/) is on the path so that
# top-level packages like Settings, Updates, etc. can always be imported,
# regardless of the working directory or PYTHONPATH at launch time.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import MainLoop
import time
import logging
import logging.handlers
from Connectivity import cpuserial
import json
# Import the new settings manager
from Settings.settings_manager import settings_manager
import MetricsLogger

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
sh.setLevel(loglevel)
logger.addHandler(sh)

if settings_manager.get("LogToServer"):
    try:
        from LoggingSecure import LoggingSecureHandler, load_logging_key
        from pathlib import Path
        version_path = Path(_project_root) / "VERSION"
        version = version_path.read_text().strip() if version_path.exists() else None
        secure_handler = LoggingSecureHandler(
            host=settings_manager.get("LogHost"),
            url=settings_manager.get("LogUrl"),
            api_key=load_logging_key(settings_manager.get("LogCredentialFile")),
            level=loglevels[settings_manager.get("LogServerLevel").lower()],
            queue_size=settings_manager.get("LogQueueSize"),
            batch_size=settings_manager.get("LogBatchSize"),
            app_version=version,
            secrets=(settings_manager.get("OTA.api_key", ""),),
        )
        logger.setLevel(min(loglevel, secure_handler.level))
        logger.addHandler(secure_handler)
    except (OSError, ValueError, KeyError):
        logger.error("Remote logging unavailable: check endpoint and protected logging credential file")

if settings_manager.get("LogToFile"):
    fh = logging.handlers.RotatingFileHandler(
        settings_manager.get("LogFilePath"),
        maxBytes=settings_manager.get("LogFileSize"), 
        backupCount=settings_manager.get("LogFileBuCount")
    )
    fh.setLevel(loglevel)
    fh.setFormatter(jsonformatter)
    logger.addHandler(fh)


MetricsLogger.setup_metrics_logger(settings_manager)


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


