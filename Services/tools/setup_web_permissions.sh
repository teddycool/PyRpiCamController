#!/bin/bash
# Setup permissions for web service to restart camera service

echo "Setting up sudo permissions for pi user to restart camera service..."

# Create sudoers rule for camera service restart
sudo tee /etc/sudoers.d/camcontroller-web <<EOF
# Allow pi user to restart camera service without password
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart camcontroller.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl stop camcontroller.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl start camcontroller.service
pi ALL=(ALL) NOPASSWD: /bin/systemctl status camcontroller.service
EOF

echo "Sudo permissions configured successfully."
echo "The web interface can now restart the camera service automatically."