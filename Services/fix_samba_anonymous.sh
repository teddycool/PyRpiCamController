#!/bin/bash
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

# Quick fix for Samba anonymous access issues
# Run this script if anonymous login stops working after a restart

echo "=== Fixing Samba Anonymous Access ==="

# Set correct permissions on shared directory
sudo chown -R pi:pi /home/pi/shared
sudo chmod -R 755 /home/pi/shared

# Remove pi user from samba and re-add without password
sudo smbpasswd -x pi 2>/dev/null || true
sudo smbpasswd -a pi -n

# Copy updated Samba configuration
sudo cp /home/pi/PyRpiCamController/Services/smb.conf /etc/samba/smb.conf

# Restart Samba services
echo "Restarting Samba services..."
sudo systemctl restart smbd
sudo systemctl restart nmbd

echo "Samba anonymous access should now be working!"
echo "Try accessing: \\\\$(hostname).local\\FileShare"
echo ""
echo "NOTE: If anonymous access still doesn't work, a full reboot may be required:"
echo "sudo reboot"