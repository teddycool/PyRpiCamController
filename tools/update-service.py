
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
__author__ = 'teddycool'

# The project is licensed under GNU GPLv3, check the LICENSE file for details.

import os
os.system("sudo systemctl stop pycam.service")
os.system("sudo cp /home/pi/tools/pycam.service  /etc/systemd/system/pycam.service") 
os.system("sudo systemctl daemon-reload")
os.system("sudo systemctl enable pycam.service")
os.system("sudo systemctl start pycam.service")
