#!/bin/bash
# Post-installation validation checklist for PyRpiCamController
# Run this after installation to verify everything is working

echo "🔍 PyRpiCamController Installation Validation"
echo "============================================"
echo "Date: $(date)"
echo "Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo

echo "📋 VALIDATION CHECKLIST:"
echo

# 1. Service Status
echo "1️⃣  Service Status:"
echo -n "   • camcontroller.service: "
if systemctl is-active camcontroller.service >/dev/null; then
    echo "✅ Running"
else
    echo "❌ Not running"
    echo "     Check with: sudo systemctl status camcontroller.service"
fi

echo -n "   • camcontroller-web.service: "
if systemctl is-active camcontroller-web.service >/dev/null; then
    echo "✅ Running"
else
    echo "❌ Not running"
    echo "     Check with: sudo systemctl status camcontroller-web.service"
fi

echo -n "   • Samba (smbd): "
if systemctl is-active smbd >/dev/null; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

echo -n "   • NetBIOS (nmbd): "
if systemctl is-active nmbd >/dev/null; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

echo

# 2. Network Connectivity
echo "2️⃣  Network Connectivity:"
LOCAL_IP=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

echo -n "   • Web interface (port 8000): "
if curl -s --connect-timeout 5 "http://localhost:8000" >/dev/null; then
    echo "✅ Accessible"
    echo "     URL: http://$HOSTNAME.local:8000"
    echo "     URL: http://$LOCAL_IP:8000"
else
    echo "❌ Not accessible"
fi

echo -n "   • Samba share: "
if command -v smbclient >/dev/null && timeout 10 smbclient //$LOCAL_IP/shared -U% -c "ls; quit" >/dev/null 2>&1; then
    echo "✅ Accessible"
    echo "     Share: smb://$HOSTNAME.local/shared"
    echo "     Share: smb://$LOCAL_IP/shared"
else
    echo "❌ Not accessible"
fi

echo

# 3. Critical Python Imports
echo "3️⃣  Python Dependencies:"

cd /home/pi/PyRpiCamController/CamController 2>/dev/null || {
    echo "❌ Project directory not found"
    exit 1
}

test_imports=(
    "numpy:import numpy"
    "cv2:import cv2"
    "picamera2:from picamera2 import Picamera2"
    "rpi_ws281x:import rpi_ws281x"
    "Vision.pipeline:from Vision.pipeline.ImageProcessor import ImageProcessor"
    "requests:import requests"
    "flask:import flask"
)

for test in "${test_imports[@]}"; do
    name="${test%:*}"
    import_cmd="${test#*:}"
    echo -n "   • $name: "
    
    if python3 -c "$import_cmd" 2>/dev/null; then
        echo "✅ OK"
    else
        echo "❌ Failed"
    fi
done

echo

# 4. File System
echo "4️⃣  File System:"
echo -n "   • Shared directory: "
if [ -d "/home/pi/shared" ]; then
    echo "✅ Exists"
    echo "     Contents: $(ls -1 /home/pi/shared | wc -l) items"
else
    echo "❌ Missing"
fi

echo -n "   • Log directory: "
if [ -d "/home/pi/shared/logs" ]; then
    echo "✅ Exists"
else
    echo "❌ Missing"
fi

echo

# 5. ComitUp WiFi (if installed)
echo "5️⃣  WiFi Management:"
echo -n "   • ComitUp CLI: "
if command -v comitup-cli >/dev/null; then
    echo "✅ Available"
    echo "     Use: comitup-cli to manage WiFi"
else
    echo "ℹ️  Not installed (manual WiFi setup required)"
fi

echo

# 6. Performance Check
echo "6️⃣  System Performance:"
echo "   • Memory usage: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "   • Disk usage: $(df -h /home | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
echo "   • Load average: $(uptime | awk -F'load average:' '{print $2}' | xargs)"

echo

# 7. Quick Functionality Test
echo "7️⃣  Quick Functionality Test:"
echo -n "   • Camera detection: "
if python3 -c "from picamera2 import Picamera2; p=Picamera2(); print('Camera found')" 2>/dev/null; then
    echo "✅ Camera detected"
else
    echo "⚠️  Camera not detected (check connections)"
fi

echo

echo "📊 SUMMARY:"
echo "=========="

# Count successes
services_ok=0
network_ok=0
python_ok=0

systemctl is-active camcontroller.service >/dev/null && ((services_ok++))
systemctl is-active camcontroller-web.service >/dev/null && ((services_ok++))
systemctl is-active smbd >/dev/null && ((services_ok++))
systemctl is-active nmbd >/dev/null && ((services_ok++))

curl -s --connect-timeout 5 "http://localhost:8000" >/dev/null && ((network_ok++))
command -v smbclient >/dev/null && timeout 10 smbclient //$LOCAL_IP/shared -U% -c "ls; quit" >/dev/null 2>&1 && ((network_ok++))

for test in "${test_imports[@]}"; do
    import_cmd="${test#*:}"
    python3 -c "$import_cmd" 2>/dev/null && ((python_ok++))
done

echo "Services: $services_ok/4 running"
echo "Network: $network_ok/2 accessible"
echo "Python: $python_ok/${#test_imports[@]} imports working"

if [ $services_ok -ge 3 ] && [ $network_ok -ge 1 ] && [ $python_ok -ge 5 ]; then
    echo
    echo "🎉 INSTALLATION SUCCESS!"
    echo "PyRpiCamController appears to be working correctly."
    echo
    echo "Next steps:"
    echo "• Access web interface: http://$HOSTNAME.local:8000"
    echo "• Configure camera settings via web interface"
    echo "• Test file sharing: smb://$HOSTNAME.local/shared"
    echo "• Configure WiFi with ComitUp if needed"
else
    echo
    echo "⚠️  INSTALLATION NEEDS ATTENTION"
    echo "Some components are not working correctly."
    echo "Check the failed items above and run:"
    echo "• sudo systemctl status camcontroller.service"
    echo "• sudo journalctl -u camcontroller.service --since '10 minutes ago'"
fi

echo
echo "For detailed logs: sudo journalctl -u camcontroller* --since today"
echo "For help: check the troubleshooting scripts in tools/ directory"