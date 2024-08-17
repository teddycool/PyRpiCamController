import json
import logging
import time
import requests

logger = logging.getLogger("cam.settings")

class Settings(object):

    def __init__(self, defaultsettingsdictionary):
        #TODO: try to set usersettings
        self.curSettings = defaultsettingsdictionary
        self._url = "http://www.biwebben.se/"
        self._settingsfromservermessage = ""
        self._settingsstarted = time.time()

    #Check if there are some new settings since last time
    def checkForNewSettings(self, cpuid):        
        updated = False
        try:
            r = requests.get(self._url + "getcamlastupdate.php?cpu=" + cpuid)
            if r.status_code == 200:  
                #Here comes a unix timestamp              
                lastupdatetimestamp = r.text
                if lastupdatetimestamp > self._settingsstarted:
                    #New settings available at server
                    updated = True
        except:
            pass
        return updated
    
    #Get the actual latest settings from server
    def getSettingsfromServer(self, cpuid):
        try:
            r = requests.get(self._url + "getcamsettings.php?cpu=" + cpuid)
            if r.status_code == 200: 
                newsettings = json.loads(r.text)
                try:
                    for setting in self.curSettings:
                        self.curSettings[setting] = newsettings[setting]         
                    logger.info("Settings updated from server")
                    logger.info("New settings %s", newsettings)
                    updated=True
                    #TODO: save new user-setting to file
                    #TODO: restart camservice with new settings
                except:
                    logger.warning("The update with new settings from server failed" , exc_info=1)
        except:
            logger.warning("Settings catched an exception when trying to update.", exc_info=1)


if __name__ == '__main__':
    print ("Testcode for Settings")
    jsonstring = '{"Cam": {"width": 800, "height": 768, "timeslot": 5, "posturl": "http://www.biwebben.se/filedump.php", "type": "outside", "timeschedule": [6, 19]}, "Limits": {"maxcputemp": 80, "wpstimeout": 120}, "Light": 80, "LogLevel": "Debug", "CheckNewSettings": 30, "MotionDetector": {"active": false, "motioncount": 200, "history": 50}, "Connectivity": {"wpstimeout": 120, "settingsbaseurl": "http://www.biwebben.se/getcamsettings.php"}}'
    settings = Settings(json.loads(jsonstring))
    print(settings.curSettings)
    settings.checkForUpdates("00000000f3a7942c")
    print(settings.curSettings)