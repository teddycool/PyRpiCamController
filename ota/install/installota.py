
import logging
from urllib import request
import time
import os

logger = logging.getLogger("otainstall")
logger.setLevel(logging.info)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#Default, always log to console ?
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)


fh = logging.handlers.RotatingFileHandler('/home/pi/logs/ota.log',maxBytes=150000, backupCount=10)
fh.setFormatter(formatter)
logger.addHandler(fh)

# TODO: add logging to backend
#hh = logging.handlers.HTTPHandler("www.biwebben.se","camlogpost.php?cpuid=" + mycpuid)
#logger.addHandler(hh)


class InstallOta(object):

    def __init__(self):
        logger.info("Installing ota for CamController is starting...")
        os.system("sudo systemctl pycam.service stop")
        logger.info("Waiting for pycam-service to stop")   
        time.sleep(15)
        self.cpuid = os.system("python /home/pi/CamController/Connectivity/cpuserial.py")
        
    def Run(self):
        # Get and store latest sw
        logger.info("Getting new sw from server")  
        response = request.urlretrieve("https://www.biwebben.se/otasw/pycam_latest.gz", "/home/pi/otasw/pycam_latest.gz")
        # Backup present sw
        logger.info("Backing up old sw")  
        logger.info("Unpacking new sw")  
        logger.info("Running some tests")  
        logger.info("Report OTA result to backend")  
        logger.info("Start the service with new sw")  
        os.system("sudo systemctl pycam.service start")
        time.sleep(30)
        logger.info("Checking if service is running")
        cnt = 0
        otasuccess = False
        
        while 1:
            time.sleep(0.5)
            cnt = cnt + 1
            if os.system("systemctl is-active pycam.service"):
                #New version of service is started and running 
                otasuccess=True
                break
            if cnt > 120:
                #Log error to backend?
                break
            
        if otasuccess:
            os.system("sudo reboot")
        else:
            #Running recovery
            pass
            
        
    def _getsw(self):
        r = requests.get("https://www.biwebben.se/getotasw.php?cpu=" + self.cpuid)
        if r.status_code == 200: 
            pass
        
        
        
if __name__ == "__main__":
    ota = InstallOta()
    ota.run()
        
        
