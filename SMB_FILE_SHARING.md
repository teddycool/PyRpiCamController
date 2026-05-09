# SMB File Sharing Guide

This guide covers the built-in SMB (Samba) file sharing feature that provides automatic network access to images and logs from your PyRpiCamController.

## 🎯 What is SMB File Sharing?

SMB (Server Message Block) file sharing allows you to access files on your Raspberry Pi camera system directly from your computer's file explorer as if they were local folders. No special software needed - it works natively with Windows, macOS, and Linux.

**Key Benefits:**
- ✅ **Zero Configuration**: Automatically set up during installation  
- ✅ **Cross-Platform**: Works with Windows, Mac, and Linux file managers
- ✅ **Guest Access**: No passwords required - just browse and access
- ✅ **Real-Time Access**: View images immediately as they're captured
- ✅ **Network Discovery**: Your Pi appears automatically in network browsers

## 📁 What's Shared?

The SMB share provides access to:

```
/home/pi/shared/
├── images/           # All captured images organized by date
│   ├── 2026-04-14/  # Today's images (YYYY-MM-DD format)
│   │   ├── 1776177632.jpg
│   │   ├── 1776177645.jpg
│   │   └── ...
│   ├── 2026-04-15/  # Tomorrow's images
│   │   └── ...
│   └── ...
├── logs/            # System and application logs
│   ├── camcontroller.log
│   ├── debug.log
│   └── smb_test.log
└── [other files]    # Any additional files placed in the shared folder
```

## 🌐 How to Access

### Windows (File Explorer)

**Method 1: Network Discovery**
1. Open File Explorer
2. Click "Network" in the left sidebar
3. Look for your Pi (hostname like `b1ce8695`)
4. Double-click to access the `shared` folder

**Method 2: Direct Connection**
1. Press `Win + R` to open Run dialog
2. Type: `\\[hostname]\shared` or `\\[ip-address]\shared`
   - Example: `\\b1ce8695\shared` or `\\192.168.1.112\shared`
3. Press Enter

**Method 3: Address Bar**
1. Open File Explorer
2. Click in the address bar
3. Type: `\\[hostname]\shared` and press Enter

### macOS (Finder)

**Method 1: Network Discovery**
1. Open Finder
2. Look in the sidebar under "Shared"
3. Click on your Pi hostname
4. Select the `shared` volume

**Method 2: Direct Connection**
1. Open Finder
2. Press `Cmd + K` (Connect to Server)
3. Type: `smb://[hostname].local/shared` or `smb://[ip-address]/shared`
   - Example: `smb://b1ce8695.local/shared` or `smb://192.168.1.112/shared`
4. Click "Connect"

**Method 3: Address Bar**
1. In Finder, press `Cmd + Shift + G` (Go to Folder)
2. Type: `smb://[hostname].local/shared`
3. Click "Go"

### Linux (File Manager)

**Method 1: Network Discovery**
1. Open your file manager (Nautilus, Dolphin, Thunar, etc.)
2. Look for "Network" or "Browse Network"
3. Find your Pi in the list
4. Click to access the shared folder

**Method 2: Direct Connection**
1. Open file manager
2. Press `Ctrl + L` or click address bar
3. Type: `smb://[hostname].local/shared` or `smb://[ip-address]/shared`
   - Example: `smb://b1ce8695.local/shared` or `smb://192.168.1.112/shared`
4. Press Enter

**Method 3: Command Line (smbclient)**
```bash
# List shares
smbclient -L //[ip-address] -U%

# Connect to specific share
smbclient //[ip-address]/shared -U%

# Mount the share
sudo mkdir /mnt/camera-share
sudo mount -t cifs //[ip-address]/shared /mnt/camera-share -o guest,uid=1000,gid=1000
```

## 🔍 Finding Your Pi's Details

If you don't know your Pi's hostname or IP address:

**On the Raspberry Pi itself:**
```bash
# Get hostname
hostname

# Get IP address
hostname -I

# Both at once
echo "Hostname: $(hostname), IP: $(hostname -I | cut -d' ' -f1)"
```

**From another computer:**
```bash
# On macOS/Linux - scan for devices named like the Pi
nmap -sn 192.168.1.0/24 | grep -B2 -A2 "b1ce8695\|raspberry"

# On Windows PowerShell
arp -a | findstr "192.168.1"
```

## 🛠️ Troubleshooting

### Share Not Appearing in Network Browser

**Check if services are running:**
```bash
# On your Pi
sudo systemctl status smbd nmbd wsdd avahi-daemon
```

**Restart services if needed:**
```bash
sudo systemctl restart smbd nmbd wsdd avahi-daemon
```

**For Windows 10/11 discovery issues:**
- Ensure "Network Discovery" is enabled in Windows
- Try accessing by IP address instead of hostname
- The `wsdd` service specifically helps Windows 10/11 discovery

### Connection Timeout or Access Denied

**Check firewall (if you have one enabled):**
```bash
# On your Pi - check if UFW is blocking
sudo ufw status

# If needed, allow SMB ports
sudo ufw allow 445/tcp
sudo ufw allow 139/tcp  
sudo ufw allow 137:138/udp
```

**Test connectivity:**
```bash
# From another computer, test if SMB port is reachable
telnet [pi-ip-address] 445

# Or use nmap
nmap -p 445 [pi-ip-address]
```

### Hostname Resolution Issues

**Use .local suffix for mDNS:**
- Instead of: `\\b1ce8695\FileShare`
- Try: `\\b1ce8695\shared` or `\\b1ce8695.local\shared` or `smb://b1ce8695.local/shared`

**Use IP address directly:**
- Find IP: `hostname -I` on your Pi
- Access: `\\192.168.1.112\shared` (replace with your actual IP)

### Permission Issues

**Reset share permissions:**
```bash
# On your Pi
sudo chmod 755 /home/pi
sudo chmod 777 /home/pi/shared
sudo chown -R pi:pi /home/pi/shared
```

### Run Full Diagnostics

**Use the built-in test script:**
```bash
# On your Pi
cd ~/PyRpiCamController
python3 tools/test_smb_service.py
```

This will check all services, configurations, and provide specific guidance for any issues found.

## ⚙️ Advanced Configuration

### Share Names

The system provides two share names for compatibility:
- **`shared`** - Primary share name (browseable)
- **`FileShare`** - Legacy alias (hidden from browse lists but still accessible)

Both point to the same location: `/home/pi/shared`

### Adding Custom Folders

You can create additional folders in the shared directory:
```bash
# On your Pi
sudo mkdir /home/pi/shared/my-custom-folder
sudo chown pi:pi /home/pi/shared/my-custom-folder
sudo chmod 755 /home/pi/shared/my-custom-folder
```

### Customizing SMB Configuration

The SMB configuration file is located at:
- **Source**: `Services/smb.conf` (in the project)
- **Active**: `/etc/samba/smb.conf` (on the Pi)

To modify the configuration:
1. Edit `Services/smb.conf` in your project
2. Copy it to the Pi: `sudo cp Services/smb.conf /etc/samba/smb.conf`
3. Restart Samba: `sudo systemctl restart smbd nmbd`

## 🔐 Security Considerations

**Current Configuration:**
- Guest access enabled (no authentication required)
- Read/write access to the shared folder
- Only accessible from your local network

**For Enhanced Security:**
If you need authentication or want to restrict access:

1. **Add SMB user authentication:**
```bash
# Create a Samba user
sudo smbpasswd -a pi

# Disable guest access in smb.conf:
# Change: guest ok = yes → guest ok = no
# Change: guest only = yes → guest only = no
```

2. **Restrict network access:**
```bash
# Add to smb.conf [global] section:
# hosts allow = 192.168.1.0/24 127.0.0.1
# hosts deny = 0.0.0.0/0
```

3. **Use firewall rules:**
```bash
# Restrict SMB access to specific IPs
sudo ufw allow from 192.168.1.100 to any port 445
sudo ufw deny 445
```

## 📊 Monitoring Usage

**Check active connections:**
```bash
# See who's connected
sudo smbstatus

# Monitor SMB logs  
sudo tail -f /var/log/samba/log.smbd
```

**Check shared folder size:**
```bash
# See disk usage
du -sh /home/pi/shared/

# Monitor in real-time
watch -n 5 'du -sh /home/pi/shared/*'
```

## 🤝 Integration with Other Tools

### Automatic Backup Scripts

Create scripts to automatically sync images to another location:

```bash
#!/bin/bash
# backup-images.sh
rsync -av --progress /home/pi/shared/images/ /backup/destination/
```

### Photo Organization Tools

Since the shared folder appears as a regular network drive, you can:
- Use photo management software directly on the network share
- Set up automatic imports into Lightroom, Photos, etc.
- Create automated processing workflows

### Development and Research

For developers and researchers:
- Direct access to logs for real-time debugging
- Immediate access to captured images for analysis
- Integration with data processing pipelines

---

**Need help?** Run the diagnostic script (`python3 tools/test_smb_service.py`) or check the [main troubleshooting guide](TROUBLESHOOTING.md) for additional support.