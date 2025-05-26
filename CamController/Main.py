import MainLoop
import time
import os
import sys
import logging
import logging.handlers
from Connectivity import cpuserial
from camconfig import defaultsettings
import json
# TODO: check for OTA at start, if enabled start with new thread, close current and restart after install

#if(ota):
#    os.system("python /home/pi/ota/installota.py &")
 
mycpuserial = cpuserial.getserial()

# TODO: get all settings from server at start...

import logging
loglevels = {"debug": logging.DEBUG, "info": logging.INFO}
try:
    loglevel = loglevels[defaultsettings["LogLevel"]]
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

if defaultsettings["LogToServer"]:
    httph = logging.handlers.HTTPHandler(host=defaultsettings["LogHost"], url=defaultsettings["LogUrl"], method="GET", secure=False)
    logger.addHandler(httph)

if defaultsettings["LogToFile"]:
    fh = logging.handlers.RotatingFileHandler(defaultsettings["LogFilePath"],maxBytes=defaultsettings["LogFileSize"], backupCount=defaultsettings["LogFileBuCount"])
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

