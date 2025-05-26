__author__ = "teddycool"
# This file is part of the BeeCam project created by Par Sundback
#
# Purpose of this file:
# Configuration for the cam, both the video-stream and the CAM framework software

# Default user-settings that can be replaced by a settings-file from server

defaultsettings = {
    "Version": 1, # version of the settings structure 
    "Mode": "Cam", # Cam or Stream   
    "OtaEnable": False, 
    "Cam": {
        "width": 4608,  # Picture width, in pixels,  maxres picam3: 4608 x 2592
        "height": 2592,  # Picture height, in pixels
        "timeslot": 15,  # Time slot in seconds between pictures
        "posturl": "where to post", 
        "brightness": 0.1,  # Exposure brightness, -1 to 1, where 0 is default, -1 is really dark and 1 is really bright     "posturl": "http://www.biwebben.se/filedump2.php",
        "timeschedule": (6, 19), # Start and stop hours... 0-24 for around the clock
        "MotionDetector": {"active": False, "motioncount": 200, "history": 50},   
        "crop": False, # Crop the image to a smaller size. NOTE: 0,0 is top left in the image vector
        "ctopleft": (300,250), #Top left corner   (x1,y1) (inclusive)
        "cbottomright": (4301,2351), #Bottom right corner (x2, y2) (exclusive)           
    },
    "Stream":{
        "width": 640,  # Stream width, in pixels,  maxres picam3: 4608 x 2592
        "height": 480,  # Stream height, in pixels
        "framerate": 20, # Framerate
        "port": 8080, # serverport
        "pagetitle": "Titel of webpage for stream",
        "h1title": "Headline of webpage for stream"
    },
    "Limits": {
        "maxcputemp": 80,
        "wcputemp": 65
    },
    "Light": 60,           #PWM value for the light intensity 0-100 (%)
    "LogLevel": "debug",
    "LogToFile": True,
    "LogFilePath": "/home/pi/logs/cam.log", 
    "LogFileSize": 1000000, 
    "LogFileBuCount": 5,
    "LogToServer": True,
    "LogHost": "your server",
    "LogUrl":"/your script", #This must be a receiving-script using GET and no security
    "CheckNewSettings": 3600,  # seconds between checks for new settings    
    "CheckCpuTemp": 60,  # seconds between checking cpu-temp    
    "Connectivity": {
        "settingsbaseurl": "where to get settings",
        "inetdetectionurl": "http://www.google.com"
    }, 
}


# ------------------------------
# The settings below is related to the hardware and should NOT be changed on the fly from the server
# IO used for display is the same for all pi-types

#generated with python and unique for each box: secrets.token_urlsafe(64)
apikey = "_your unique api key_"; 

hwconfig = {
    "Version": 1, # version of the settings structure 
    "CamChip": "PiCam3",  
    "RpiBoard": "Rpi3B+", 
    "LightBox": True,
    "Io": {  # All pins defined as GPIO aka GPIO.BCM mode
        "lightcontrolgpio": 12,  #only works with a PWM0 pin
        "displaycontrolgpio": 18, #only works with a PWM0 pin
        "displaysize": 1,  # number of leds
    },
}

