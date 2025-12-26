# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

# Install-script for PyRpiCamController - Complete system setup
# Installs all dependencies, services, and configures the system for camera operation
# 
# Features installed:
# - Camera controller with unified settings system
# - Swedish web interface for configuration  
# - Samba file sharing for remote access
# - ComitUp for easy WiFi setup
# - OTA update system (ready but commented out)
# 
# NOTE: Intended for RPi3B+ but works with other models
# For Pi Zero models: enlarge swap file before installation
# Adjust swap: https://pimylifeup.com/raspberry-pi-swap-file/

# Note: The old configfilepath has been removed - now using unified settings system

# NOTE: This script assumes the PyRpiCamController project has been cloned/copied to:
#       /home/pi/PyRpiCamController/
# 
# To deploy the project before running this installer:
# 1. Clone: git clone https://github.com/teddycool/PyRpiCamController.git /home/pi/PyRpiCamController
# 2. OR: Copy the entire project directory to /home/pi/PyRpiCamController/

import os
import time

startime = time.time()

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
  return cpuserial.lstrip("0") #Remove leading zeros


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
  
  # Pre-flight checks
  print("* Checking project deployment...")
  if not os.path.exists("/home/pi/PyRpiCamController"):
      print("ERROR: PyRpiCamController project not found at /home/pi/PyRpiCamController/")
      print("Please clone or copy the project first:")
      print("git clone https://github.com/teddycool/PyRpiCamController.git /home/pi/PyRpiCamController")
      exit(1)
      
  required_dirs = [
      "/home/pi/PyRpiCamController/CamController",
      "/home/pi/PyRpiCamController/Settings", 
      "/home/pi/PyRpiCamController/WebGui",
      "/home/pi/PyRpiCamController/tools"
  ]
  
  for dir_path in required_dirs:
      if not os.path.exists(dir_path):
          print(f"ERROR: Required directory not found: {dir_path}")
          print("Please ensure the complete project is deployed.")
          exit(1)
  
  print("* Project deployment verified ✓")

  os.system("sudo apt update -y")

  print("*****************************************")
  print("Installing needed packages")
  print("*****************************************")

  # Core Python and camera support
  os.system("sudo apt install -y python3-pip")
  os.system("sudo apt install -y python3-picamera2")
  os.system("sudo apt install -y libcamera-apps")  # Camera applications
  os.system("sudo apt install -y python3-libcamera")
  
  # LED strip control (system-wide for hardware access)
  os.system("sudo pip install rpi-ws281x --break-system-packages")
  
  # GPIO support - Install lgpio for modern GPIO access
  os.system("sudo apt install -y python3-lgpio python3-rpi.gpio")
  
  # Add pi user to gpio group for GPIO access
  os.system("sudo usermod -a -G gpio pi")
  
  # Computer vision and image processing
  os.system("sudo apt install -y python3-opencv")
  os.system("sudo apt install -y opencv-data")
  os.system("sudo apt install -y ffmpeg")
  os.system("sudo pip install simplejpeg --break-system-packages")
  
  # HTTP requests and web functionality  
  os.system("sudo pip install requests --break-system-packages")
  
  # System utilities
  os.system("sudo apt install -y git")  # For OTA and general development
  os.system("sudo apt install -y curl")  # For web requests
  
  # Additional camera dependencies (if needed)
  #os.system("sudo apt install -y libcamera-dev libepoxy-dev libjpeg-dev libtiff5-dev")

  print("*****************************************")
  print("* Setting up unified settings system...")
  print("*****************************************")
  
  # Note: Assumes the PyRpiCamController project is already copied to /home/pi/PyRpiCamController
  # during initial deployment. The unified settings system is already in place.
  
  # Verify settings system is in place
  if not os.path.exists("/home/pi/PyRpiCamController/Settings"):
      print("* ERROR: Settings directory not found. Ensure PyRpiCamController is properly deployed.")
      exit(1)
  
  if not os.path.exists("/home/pi/PyRpiCamController/WebGui"):
      print("* ERROR: WebGui directory not found. Ensure PyRpiCamController is properly deployed.")
      exit(1)
      
  print("* Unified settings system and web interface found and ready.")
  print("* Using unified settings system (legacy config files no longer needed).")

  print("*****************************************")
  print("* Setting up the pycam service")
  print("*****************************************")

  os.system("sudo cp /home/pi/PyRpiCamController/CamController/camcontroller.service  /etc/systemd/system/camcontroller.service") 
  #Changed.. https://www.thedigitalpictureframe.com/ultimate-guide-systemd-autostart-scripts-raspberry-pi/
  #sudo chmod 644 /etc/systemd/system/name-of-your-service.service
  os.system("sudo systemctl daemon-reload")
  os.system("sudo systemctl enable camcontroller.service")

  
# Setup as from Dave Steel, comitup
  print("*****************************************")
  print("* Installing commitup and reset the network")
  print("*****************************************")


  os.system("sudo wget https://davesteele.github.io/comitup/deb/davesteele-comitup-apt-source_1.3_all.deb")
  os.system("sudo dpkg -i davesteele-comitup-apt-source*.deb")
  os.system("sudo apt-get update")
  os.system("sudo apt-get install -y comitup comitup-watch")
  os.system("sudo cp /home/pi/PyRpiCamController/Services/comitup.conf /etc/comitup.conf")
  os.system("sudo rm /etc/network/interfaces")
  os.system("sudo systemctl mask dnsmasq.service")
  os.system("sudo systemctl mask systemd-resolved.service")
  os.system("sudo systemctl mask dhcpd.service")
  os.system("sudo systemctl mask dhcpcd.service")
  os.system("sudo systemctl mask wpa-supplicant.service")
  os.system("sudo systemctl enable NetworkManager.service")
  os.system("sudo touch /boot/ssh")


  print("*****************************************")
  print("Create the project directory structure")
  print("*****************************************")

  # Main shared directories
  os.system("mkdir -p /home/pi/shared")
  os.system("chmod 777 /home/pi/shared")
  os.system("mkdir -p /home/pi/shared/images")
  os.system("chmod 777 /home/pi/shared/images")
  os.system("mkdir -p /home/pi/shared/logs")
  os.system("chmod 777 /home/pi/shared/logs")
  
  # Additional project directories
  os.system("mkdir -p /home/pi/PyRpiCamController")
  
  # Timelapse directory (optional)
  os.system("mkdir -p /home/pi/timelapse")
  os.system("chmod 755 /home/pi/timelapse")
  

  print("*****************************************")
  print("*Install SAMBA file-sharing")
  print("*****************************************")
  os.system("sudo apt update")
  os.system("sudo apt install -y samba samba-common-bin")
  
  # Set up proper permissions for shared directory
  os.system("sudo chown -R pi:pi /home/pi/shared")
  os.system("sudo chmod -R 755 /home/pi/shared")
  
  # Add pi user to samba (without password for guest access)
  os.system("sudo smbpasswd -a pi -n")  # Add pi user with no password
  
  # Copy and apply Samba configuration
  os.system("sudo cp /home/pi/PyRpiCamController/Services/smb.conf /etc/samba/smb.conf")
  
  # Restart Samba services
  os.system("sudo systemctl restart smbd")
  os.system("sudo systemctl restart nmbd")

  print("*****************************************")
  print("*Install Flask web-server and web-gui for config")
  print("*****************************************")
  os.system("sudo pip3 install flask --break-system-packages")

  os.system("sudo apt install -y gunicorn")
  os.system("sudo cp /home/pi/PyRpiCamController/WebGui/camcontroller-web.service  /etc/systemd/system/camcontroller-web.service")
  os.system("sudo systemctl daemon-reload")
  os.system("sudo systemctl enable camcontroller-web")
  os.system("sudo systemctl start camcontroller-web")
  
  # OTA (Over-The-Air) Update System Setup (COMMENTED OUT - API not yet deployed)
  # print("*****************************************")
  # print("*Install Update System")
  # print("*****************************************")
  # 
  # # Create Updates directories
  # os.system("sudo mkdir -p /home/pi/Updates")
  # os.system("sudo mkdir -p /home/pi/Updates/bu")      # Backup directory
  # os.system("sudo mkdir -p /home/pi/Updates/sw")      # Software staging directory
  # os.system("sudo chmod 755 /home/pi/Updates")
  # 
  # # Copy Updates files
  # os.system("sudo cp -r /home/pi/Updates/install /home/pi/Updates/")
  # os.system("sudo cp /home/pi/Updates/recovery.sh /home/pi/Updates/")
  # os.system("sudo chmod +x /home/pi/Updates/recovery.sh")
  # 
  # # Install and enable update daemon service
  # os.system("sudo cp /home/pi/Updates/camcontroller-update.service /etc/systemd/system/camcontroller-update.service")
  # os.system("sudo systemctl daemon-reload")
  # os.system("sudo systemctl enable camcontroller-update")
  # # Note: Don't start update daemon until server API is ready and settings are configured
  # print("* Update daemon installed but not started - configure settings first")


  print("*****************************************")
  print("* Setting new hostname...")
  print("*****************************************")
  hostname = getserial()
  os.system("sudo hostnamectl set-hostname " + hostname)
  print("Hostname is now: " + hostname + " (activates after reboot)")
  print("")
  print("")
  print("*****************************************")  
  print("Installation Summary:")
  print("*****************************************") 
  print("Project structure created:")
  print("- /home/pi/PyRpiCamController/ - Main application")
  print("- /home/pi/shared/images/      - Image storage")
  print("- /home/pi/shared/logs/        - All system logs (accessible via network)")
  print("- /home/pi/timelapse/         - Timelapse directory")
  print("- /home/pi/Settings/          - Unified settings system")
  print("- /home/pi/WebGui/            - Web interface")
  print("- /home/pi/Updates/           - Update system (ready but not active)")
  print("")
  
  print("Services installed and enabled:")
  print("- camcontroller.service     - Main camera application")
  print("- camcontroller-web.service - Web configuration interface")
  # print("- camcontroller-update.service - OTA update daemon (installed but not started)")
  print("- smbd.service     - Samba file sharing")
  print("")
  
  print("Network access:")
  print("- Hostname: " + getserial() + ".local")
  print("- Web GUI: http://"+ getserial() +".local:8000")
  print("- Samba share: \\\\"+ getserial() +".local\\shared")
  print("")
  
  print("Available disk space:")
  os.system("df -h")
  print("")
  
  endtime = time.time()

  #sudo nano /etc/hosts
  #edit to add/change the line: 127.0.1.1   <new hostname>

  print("*****************************************")
  print("* Installation is now completed!")
  print("* Time for the install: " + str(int(endtime-startime)) + " seconds")
  print("* Network might need to be re-configured with commitup after restart!")
  print("*****************************************")
  print("")
  print("To get started:")
  print("1: Connect to the CamController AP (ComitUp) and configure WiFi:")
  print("   - Open http://10.41.0.1 to set up network connection")
  print("2: Configure camera settings via web interface:")
  print("   - Open http://"+ getserial() +".local:8000 after reboot")
  print("   - Use Basic/Advanced tabs for different setting levels")
  print("3: Access files via Samba network share:")
  print("   - Windows: \\\\"+ getserial() +".local\\shared")
  print("   - Linux/Mac: smb://"+ getserial() +".local/shared")
  print("4: Monitor logs and images via network share:")
  print("   - All logs are in /home/pi/shared/logs/ (accessible via Samba)")
  print("   - Images are in /home/pi/shared/images/ (accessible via Samba)")
  # print("5: Enable OTA updates (when server API is ready):")
  # print("   - Configure OTA settings in web interface")
  # print("   - Start ota-daemon service: sudo systemctl start ota-daemon")

except KeyboardInterrupt:
  print("Install aborted by user...")
  exit(0)
except Exception as e:
  print("Install catched an exception:", e)
  exit(1)

try:
  input("Press Enter to continue and reboot with the new services, or ctrl+C to return to prompt...")
except KeyboardInterrupt:
  print("Stopped by user, returning to prompt...")
  print("A reboot is needed to activate the new services, run 'sudo reboot' to do so.")
  exit(0)

print("*****************************************")
print("Now rebooting in 5 sec.....")
time.sleep(5)
os.system("sudo reboot")
