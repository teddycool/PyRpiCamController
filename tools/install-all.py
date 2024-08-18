#Install-script for CamController, run as root

# NOTE:  For zero and zero v2 the swap-file needs to be enlarged or the install fails.
# Adjust swap: https://pimylifeup.com/raspberry-pi-swap-file/


#Need to be changed to fit the hardware and wanted config
configfilepath = "/home/pi/tools/camconfig-tmpl.py"

import os
import time

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

try:
  print("*****************************************")
  print("Starting to update and install")
  print("Serial number: " + getserial())
  print("Model: " + detect_model())
  print("*****************************************")

  os.system("sudo apt update -y")

  print("*****************************************")
  print("Installing needed packages")
  print("*****************************************")

  os.system("sudo apt install -y python3-pip")
  os.system("sudo apt install -y python3-picamera2")
  os.system("sudo pip install rpi-ws281x --break-system-packages")  #System-wide, without venv

  os.system("sudo apt install -y python3-opencv")
  os.system("sudo apt install -y opencv-data")
  os.system("sudo apt install -y ffmpeg")
  #is this needed?
  #os.system("sudo apt install -y libcamera-dev libepoxy-dev libjpeg-dev libtiff5-dev")
  os.system("sudo pip install simplejpeg --break-system-packages")

  print("*****************************************")
  print("* Copy correct settings for CamController...")
  os.system("sudo cp " + configfilepath + " /home/pi/CamController/config.py")

  print("*****************************************")
  print("* Setting up the pycam service")
  print("*****************************************")

  os.system("sudo cp /home/pi/tools/pycam.service  /etc/systemd/system/pycam.service") #Changd.. https://www.thedigitalpictureframe.com/ultimate-guide-systemd-autostart-scripts-raspberry-pi/
  #sudo chmod 644 /etc/systemd/system/name-of-your-service.service
  os.system("sudo systemctl daemon-reload")
  os.system("sudo systemctl enable pycam.service")

  
# Setup as from Dave Steel, comitup
  print("*****************************************")
  print("* Installing commitup and reset the network")
  print("*****************************************")

  os.system("sudo wget https://davesteele.github.io/comitup/deb/davesteele-comitup-apt-source_1.2_all.deb")
  os.system("sudo dpkg -i --force-all davesteele-comitup-apt-source_1.2_all.deb")
  os.system("sudo rm davesteele-comitup-apt-source_1.2_all.deb")
  os.system("sudo apt-get update")
  os.system("sudo apt-get install -y comitup comitup-watch")
  os.system("sudo cp /home/pi/tools/comitup.conf /etc/comitup.conf")  
  os.system("sudo rm /etc/network/interfaces")
  os.system("sudo systemctl mask dnsmasq.service")
  os.system("sudo systemctl mask systemd-resolved.service")
  os.system("sudo systemctl mask dhcpd.service")
  os.system("sudo systemctl mask dhcpcd.service")
  os.system("sudo systemctl mask wpa-supplicant.service")
  os.system("sudo systemctl enable NetworkManager.service")
  os.system("sudo touch /boot/ssh")

  print("*****************************************")
  print("* Setting new hostname...")
  os.system("sudo hostnamectl set-hostname " + getserial())
  print("Hostname is now: " + getserial())

  #TODO: setup instance in db with ssh pw and basic config

  print("*****************************************")
  print("Network needs to be re-configurated with commitup after restart!")
  input("Press Enter to continue and reboot with new services, or cntrl+C to return to prompt...")
  print("*****************************************")
  print("Now rebooting in 5 sec.")

  time.sleep(5)
  os.system("sudo reboot")


except (KeyboardInterrupt):
   print("Stopped by user...")
except:
   print("Installed catched exception: ", exc_info=1)

  # #TODO
