
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
__author__ = 'teddycool'

# The project is licensed under GNU GPLv3, check the LICENSE file for details.

import os
os.system("sudo systemctl stop camcontroller.service")
os.system("sudo cp /home/pi/PyRpiCamController/CamController/camcontroller.service  /etc/systemd/system/camcontroller.service") 
os.system("sudo systemctl daemon-reload")
os.system("sudo systemctl enable camcontroller.service")
os.system("sudo systemctl start camcontroller.service")
