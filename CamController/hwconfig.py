# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

# Purpose of this file:
# Fixed configurations for the different types of hardware sold by sensorwebben.se 
# This file should not be changed by the user, unless you know what you know what you are doing.


hwconfig1 = {
    "Description": "RPi3B+ with PiCam3 and lightbox",
    "Version": 1, # version of the settings structure      
    "RpiBoard": "Rpi3B+", 
    "CamChip": "PiCam3",  # PiCam2, PiCamHQ, PiCam3, WebCam
    "LightBox": True,
    "Io": {  # All pins defined as GPIO aka GPIO.BCM mode
        "lightcontrolgpio": 12,  #only works with a PWM0 pin
        "displaycontrolgpio": 18, #only works with a PWM0 pin
        "displaysize": 1,  # number of leds
    },
}


