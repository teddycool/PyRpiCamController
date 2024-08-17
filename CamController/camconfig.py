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
        "timeslot": 30,  # Time slot in seconds between pictures
        "posturl": "http://www.biwebben.se/filedump2.php",
        "timeschedule": (6, 19), # Start and stop hours... 0-24 for around the clock
        "MotionDetector": {"active": False, "motioncount": 200, "history": 50},                                 
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
    "Light": 70,           #PWM value for the light intensity 0-100 (%)
    "LogLevel": "debug",
    "LogToFile": True,
    "LogFilePath": "/home/pi/logs/cam.log", 
    "LogFileSize": 15000, 
    "LogFileBuCount": 10,
    "LogToServer": True,
    "LogHost": "www.biwebben.se",
    "LogUrl":"/postcamlog.php", #This must be a receiving-script using GET and no security
    "CheckNewSettings": 3600,  # seconds between checks for new settings    
    "CheckCpuTemp": 60,  # seconds between checking cpu-temp    
    "Connectivity": {
        "settingsbaseurl": "http://www.biwebben.se/getcamsettings.php",
        "inetdetectionurl": "http://www.google.com"
    }, 
}


# ------------------------------
# The settings below is related to the hardware and should NOT be changed on the fly from the server
# IO used for display is the same for all pi-types

hwconfig = {
    "Version": 1, # version of the settings structure 
    "CamChip": "PiCam3",  
    "RpiBoard": "PiZeroW", 
    "LightBox": False,
    "Io": {  # All pins defined as GPIO aka GPIO.BCM mode
        "lightcontrolgpio": 12,  #only works with a PWM0 pin
        "displaycontrolgpio": 18, #only works with a PWM0 pin
        "displaysize": 1,  # number of leds
    },
}

