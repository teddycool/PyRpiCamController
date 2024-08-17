__author__ = 'teddycool'
#REF: https://lb.raspberrypi.org/forums/viewtopic.php?t=185244

import subprocess

class TempMonitor(object):

    def __init(self):
        print ("Init temp.-monitoring")

    def initialize(self):
        pass

#Read cpu temp
    def get_cpu_temperature(self):
        #get cpu temperature using vcgencmd
        process = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
        output, _error = process.communicate()
       # print(output)
        return float(output[5:9])  #Return temperature like 43.5



if __name__ == '__main__':
    print ("Testcode for TempMonitor")
    tm = TempMonitor()
    print (tm.get_cpu_temperature())