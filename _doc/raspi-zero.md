# Raspberry Pi Zero Setup Guide

## How to adjust swap on Zero and Zero v2

For Raspberry Pi Zero and Zero v2 the swap-file needs to be enlarged to at least 2GB for the install to work.

This is done by editing the file `/etc/dphys-swapfile` and changing the `CONF_SWAPSIZE` to 2048 (or more if you want).

You can do this by running the following commands:

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
```

Change `CONF_SWAPSIZE` to 2048 (or more if you want) and save the file. Then run:

```bash
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Why This Is Needed

- **Limited RAM**: Pi Zero models have only 512MB RAM
- **Compilation Requirements**: Some packages need more memory during installation
- **Swap File**: Provides virtual memory to handle memory-intensive operations
- **Temporary**: Can be reduced after installation is complete

## After Installation

Once the PyRpiCamController installation is complete, you can optionally reduce the swap size back to the default:

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE back to 100
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```