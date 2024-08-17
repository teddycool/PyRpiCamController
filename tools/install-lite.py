#Install-script for zerocam
#Use this on a 'master-sdcard' and save the image for cloning later

import os

def getserial():
  # Extract serial from cpuinfo file
  cpuserial = "0000000000000000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:6]=='Serial':
        cpuserial = line[10:26]
    f.close()
  except:
    cpuserial = "ERROR000000000"
  return cpuserial


def detect_model() -> str:
    with open('/proc/device-tree/model') as f:
        model = f.read()
    return model

print("*****************************************")
print("Starting to update and install")
print("Serial number: " + getserial())
print("Model: " + detect_model())
print("*****************************************")

os.system("sudo apt update -y")
#os.system("sudo apt full-upgrade -y")

print("*****************************************")
print("Installing needed packages")
print("*****************************************")

os.system("sudo apt install -y python3-pip")
os.system("sudo apt install -y python3-picamera2")
os.system("sudo pip install rpi-ws281x --break-system-packages")  #System-wide, without venv

os.system("sudo apt install -y python3-opencv")
os.system("sudo apt install -y opencv-data")
os.system("sudo apt install -y libcamera-dev libepoxy-dev libjpeg-dev libtiff5-dev")
os.system("sudo pip install simplejpeg --break-system-packages")

# print("Installing latest PyBeeCam sw")
# print("-----------------------------")

# The COMPLETE software with the correct structure, from github


#get the latest zip-file from biwebben
#rename old PyBeeCam-folder if present
#unpack new version to PyBeeCam-folder and tools-folder

