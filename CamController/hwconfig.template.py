# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

# Purpose of this file:
# Device-unique hardware configuration template for installer-generated hwconfig.py.
# Do not edit generated hwconfig.py manually unless you know exactly what you are doing.

hwconfig1 = {
    "Description": "{{DESCRIPTION}}",
    "Version": 1,
    "RpiBoard": "{{RPI_BOARD}}",
    "CamChip": "{{CAM_CHIP}}",  # PiCam2, PiCamHQ, PiCam3, WebCam
    "LightBox": {{LIGHTBOX}},
    "Io": {
        "lightcontrolgpio": {{LIGHT_GPIO}},
        "displaycontrolgpio": {{DISPLAY_GPIO}},
        "displaysize": {{DISPLAY_SIZE}},
        "ds18b20pin": {{DS18B20_PIN}},
    },
}
