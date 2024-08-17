__author__ = 'teddycool'

#https://github.com/rpi-ws281x/rpi-ws281x-python

import time
from rpi_ws281x import *
import logging
logger = logging.getLogger("cam.IO.display")


LED_FREQ_HZ= 800000
LED_DMA= 10
LED_BRIGHTNESS= 50
LED_INVERT= False


class Display(object):

    def __init__(self, displaygpio, displaysize):
        logger.info ("Init Display object...")
        self._displaygpio = displaygpio
        self._displaysize = displaysize
        self._displayArray = Adafruit_NeoPixel(self._displaysize , self._displaygpio, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
        self._displayArray.begin()

    def off(self):
        logger.debug ("Off pattern...")
        for i in range(self._displaysize ):
            self._displayArray.setPixelColor(i, Color(0, 0, 0, ))
        self._displayArray.show()

        
    def wifi_connected(self):
        logger.debug ("WiFi connected to internet pattern...")
        for i in range(self._displaysize ):
            self._displayArray.setPixelColor(i, Color(0, 50, 0, ))
        self._displayArray.show()

   
    def image_post(self):
        logger.debug ("Image post pattern...")
        for i in range(self._displaysize ):
            self._displayArray.setPixelColor(i, Color(5, 0, 50, ))
        self._displayArray.show()

    def no_internet(self):
        logger.debug ("No internet pattern...")
        for i in range(self._displaysize ):
            self._displayArray.setPixelColor(i, Color(50, 0, 0, ))
        self._displayArray.show()



if __name__ == '__main__':
    print ("Testcode for Display")
    cd= Display(18, 3)
    cd.showInitPattern()
    time.sleep(1)
    cd.off()
    try:
        while (True):
            cd.image_post()
            time.sleep(1)
            cd.off()
            cd.no_internet()
            time.sleep(1)
            cd.off()
            cd.wifi_connected()
            time.sleep(1)
            cd.off()
            print ("Testcode running...")
    except:
        cd.off()
        print ("Testcode ended")
       



