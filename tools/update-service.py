
import os
os.system("sudo systemctl stop pycam.service")
os.system("sudo cp /home/pi/tools/pycam.service  /etc/systemd/system/pycam.service") 
os.system("sudo systemctl daemon-reload")
os.system("sudo systemctl enable pycam.service")
os.system("sudo systemctl start pycam.service")
