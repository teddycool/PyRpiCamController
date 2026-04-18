# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import RPi.GPIO as GPIO
import time


class Light(object):
    def __init__(self, GPIO, pin, frequency=2500):
        self._gpio = GPIO
        self._gpio.setup(pin, GPIO.OUT)  # PWM pin
        self._softpwm = self._gpio.PWM(pin, frequency)    # pin, frequency from settings


    def start(self, duty):
        self._softpwm.start(duty)

    def set_duty(self, duty):
        self._softpwm.ChangeDutyCycle(duty)
        
    def stop(self):
        self.set_duty(0)        
        self._softpwm.stop()
        

if __name__ == '__main__':
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    pwmlight = Light(GPIO, 12, frequency=2500)  # Use 2500Hz for flicker-free operation
    pwmlight.start(50)
    print("Light started on 12 with 50% at 2500Hz")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Light stopped")
        pwmlight.stop()
        GPIO.cleanup()