
import os





os.system("sudo wget https://davesteele.github.io/comitup/latest/davesteele-comitup-apt-source_latest.deb")
os.system("sudo dpkg -i --force-all davesteele-comitup-apt-source_latest.deb")
os.system("sudo rm davesteele-comitup-apt-source_latest.deb")
os.system("sudo apt-get update")
os.system("sudo apt-get install -y comitup comitup-watch")
os.system("sudo m /etc/network/interfaces")
os.system("sudo systemctl mask dnsmasq.service")
os.system("sudo systemctl mask systemd-resolved.service")
os.system("sudo systemctl mask dhcpd.service")
os.system("sudo systemctl mask dhcpcd.service")
os.system("sudo systemctl mask wpa-supplicant.service")
os.system("sudo systemctl enable NetworkManager.service")
os.system("sudo touch /boot/ssh")