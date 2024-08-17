import RPi.GPIO as GPIO
import time


class Light(object):
    def __init__(self, GPIO, pin):
        self._gpio = GPIO
        self._gpio.setup(pin, GPIO.OUT)  # PWM pin
        self._softpwm = self._gpio.PWM(pin, 2000)    # pin, frequency


    def start(self, duty):
        self._softpwm.start(duty)

    def setDuty(self, duty):
        self._softpwm.ChangeDutyCycle(duty)
        
    def stop(self):
        self.setDuty(0)        
        self._softpwm.stop()
        

if __name__ == '__main__':
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    pwmlight = Light(GPIO, 12)
    pwmlight.start(50)
    print("Light started on 12 with 50%")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Light stopped")
        pwmlight.stop()
        GPIO.cleanup()