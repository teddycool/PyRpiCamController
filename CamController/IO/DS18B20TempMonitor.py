# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import os
import glob
import time
import logging

logger = logging.getLogger("cam.IO.ds18b20temp")


class DS18B20TempMonitor(object):
    """
    DS18B20 Digital Temperature Sensor Monitor
    
    This class provides interface to DS18B20 1-wire digital temperature sensors.
    The sensor must be connected to a GPIO pin configured for 1-wire protocol.
    
    Note: Requires 1-wire interface to be enabled in /boot/config.txt:
    dtoverlay=w1-gpio,gpiopin=X (where X is the GPIO pin number)
    """

    def __init__(self, pin):
        """
        Initialize DS18B20TempMonitor
        
        Args:
            pin (int): GPIO pin number where DS18B20 sensor is connected
        """
        logger.info("Init DS18B20 temperature monitoring on GPIO pin %s", pin)
        self._pin = pin
        self._base_dir = '/sys/bus/w1/devices/'
        self._device_folder = None
        self._device_file = None
        self._initialize_sensor()

    def _initialize_sensor(self):
        """Initialize 1-wire modules and find sensor device"""
        try:
            # Load required kernel modules
            os.system('modprobe w1-gpio')
            os.system('modprobe w1-therm')
            
            # Give modules time to load
            time.sleep(1)
            
            # Find the sensor device
            device_folders = glob.glob(self._base_dir + '28*')
            if not device_folders:
                logger.error("No DS18B20 sensors found. Check wiring and 1-wire configuration.")
                raise RuntimeError("No DS18B20 sensors detected")
            
            # Use the first sensor found (most setups have only one)
            self._device_folder = device_folders[0]
            self._device_file = self._device_folder + '/w1_slave'
            logger.info("Found DS18B20 sensor: %s", os.path.basename(self._device_folder))
            
        except Exception as e:
            logger.error("Failed to initialize DS18B20 sensor: %s", str(e))
            raise

    def _read_temp_raw(self):
        """Read raw temperature data from sensor file"""
        try:
            with open(self._device_file, 'r') as f:
                lines = f.readlines()
            return lines
        except IOError as e:
            logger.error("Error reading DS18B20 sensor data: %s", str(e))
            return None

    def get_temperature(self):
        """
        Read temperature from DS18B20 sensor
        
        Returns:
            float: Temperature in Celsius, or None if reading failed
        """
        if not self._device_file:
            logger.error("DS18B20 sensor not initialized")
            return None
            
        try:
            lines = self._read_temp_raw()
            if not lines:
                return None
                
            # Check if reading is valid (should end with YES)
            while lines[0].strip()[-3:] != 'YES':
                time.sleep(0.2)
                lines = self._read_temp_raw()
                if not lines:
                    logger.error("Failed to get valid reading from DS18B20")
                    return None
            
            # Extract temperature from the second line
            equals_pos = lines[1].find('t=')
            if equals_pos != -1:
                temp_string = lines[1][equals_pos + 2:]
                temp_celsius = float(temp_string) / 1000.0
                logger.debug("DS18B20 temperature: %.1f°C", temp_celsius)
                return temp_celsius
            else:
                logger.error("Temperature data not found in DS18B20 response")
                return None
                
        except Exception as e:
            logger.error("Error reading DS18B20 temperature: %s", str(e))
            return None

    def is_available(self):
        """
        Check if the sensor is available and responding
        
        Returns:
            bool: True if sensor is available, False otherwise
        """
        return self._device_file is not None and os.path.exists(self._device_file)


if __name__ == '__main__':
    print("Testcode for DS18B20TempMonitor")
    
    # Test with pin 12 (as configured in hwconfig.py)
    try:
        temp_monitor = DS18B20TempMonitor(12)
        
        if temp_monitor.is_available():
            print(f"DS18B20 sensor is available")
            
            # Read temperature a few times
            for i in range(3):
                temp = temp_monitor.get_temperature()
                if temp is not None:
                    print(f"Reading {i+1}: {temp:.1f}°C")
                else:
                    print(f"Reading {i+1}: Failed to read temperature")
                time.sleep(1)
        else:
            print("DS18B20 sensor is not available")
            
    except Exception as e:
        print(f"Error: {e}")