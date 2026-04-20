# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'
#REF: https://lb.raspberrypi.org/forums/viewtopic.php?t=185244

import subprocess

class CpuTempMonitor(object):
    """
    CPU Temperature Monitor using vcgencmd
    
    This class provides access to Raspberry Pi CPU temperature readings
    using the vcgencmd utility available on Raspberry Pi systems.
    """

    def __init__(self):
        print ("Init CPU temperature monitoring")

    def initialize(self):
        pass

    def get_cpu_temperature(self):
        """
        Read CPU temperature using vcgencmd
        
        Returns:
            float: Temperature in Celsius, or None if reading failed
        """
        try:
            #get cpu temperature using vcgencmd
            process = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate(timeout=5)
            
            if process.returncode != 0:
                print(f"vcgencmd failed with return code {process.returncode}: {error.decode()}")
                return None
                
            # Parse output like "temp=43.5'C"
            temp_str = output.decode().strip()
            if 'temp=' in temp_str:
                temp_value = temp_str.split('=')[1].replace("'C", "")
                return float(temp_value)
            else:
                print(f"Unexpected vcgencmd output: {temp_str}")
                return None
                
        except subprocess.TimeoutExpired:
            print("vcgencmd command timed out")
            return None
        except (ValueError, IndexError) as e:
            print(f"Error parsing temperature: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error reading CPU temperature: {e}")
            return None



if __name__ == '__main__':
    print ("Testcode for CpuTempMonitor")
    tm = CpuTempMonitor()
    print (tm.get_cpu_temperature())