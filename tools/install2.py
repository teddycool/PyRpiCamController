import os

print("*****************************************")
print("Installing commitup and reset the network")
print("*****************************************")
os.system("sudo apt-get install -y comitup")
os.system("sudo systemctl enable NetworkManager.service")
os.system("sudo mv /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf_old")
os.system("sudo cp /home/pi/tools/comitup.conf /etc/comitup.conf")


print("*****************************************")
print("Network needs to be configurated with commitup after restart!")
input("Press Enter to continue and reboot...")

os.system("sudo reboot")