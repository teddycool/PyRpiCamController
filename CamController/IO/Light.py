# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import logging

logger = logging.getLogger("cam.light")


class Light(object):
    def __init__(self, GPIO, pin, frequency=2500, allow_pigpio=True):
        self._gpio = GPIO
        self._pin = pin
        self._frequency = int(frequency)
        self._duty = 0.0
        self._started = False
        self._backend = None
        self._pigpio = None
        self._pigpio_client = None
        self._lgpio = None
        self._lgpio_handle = None
        pigpio_error = None
        lgpio_error = None

        # Prefer true hardware PWM via pigpio when available.
        if allow_pigpio:
            try:
                import pigpio

                hardware_pwm_pins = {12, 13, 18, 19}
                if self._pin not in hardware_pwm_pins:
                    raise RuntimeError(f"GPIO {self._pin} does not support pigpio hardware PWM")

                pigpio_client = pigpio.pi()
                if not pigpio_client.connected:
                    raise RuntimeError("pigpio daemon not reachable")

                self._pigpio = pigpio
                self._pigpio_client = pigpio_client
                self._backend = "pigpio"
                logger.info("Light PWM backend: pigpio")
                return
            except Exception as e:
                pigpio_error = e
                logger.warning("pigpio backend unavailable: %s", e)
        else:
            pigpio_error = RuntimeError("pigpio disabled for this Light instance")

        try:
            import lgpio

            self._lgpio = lgpio
            self._lgpio_handle = self._lgpio.gpiochip_open(0)
            self._lgpio.gpio_claim_output(self._lgpio_handle, self._pin, 0)
            self._backend = "lgpio"
            logger.info("Light PWM backend: lgpio")
            return
        except Exception as e:
            lgpio_error = e

        raise RuntimeError(
            "No supported hardware PWM backend available for Light. "
            f"pigpio error: {pigpio_error}; lgpio error: {lgpio_error}. "
            "RPi.GPIO software PWM fallback is disabled by design."
        )

    @staticmethod
    def _clamp_duty(duty):
        return max(0.0, min(100.0, float(duty)))

    def _apply_lgpio_pwm(self):
        self._lgpio.tx_pwm(
            self._lgpio_handle,
            self._pin,
            int(self._frequency),
            float(self._duty),
        )

    def _apply_pigpio_pwm(self):
        duty_ppm = int(round(self._duty * 10000.0))
        self._pigpio_client.hardware_PWM(self._pin, int(self._frequency), duty_ppm)


    def start(self, duty):
        self._duty = self._clamp_duty(duty)
        if self._backend == "pigpio":
            self._apply_pigpio_pwm()
        else:
            self._apply_lgpio_pwm()
        self._started = True

    def set_duty(self, duty):
        self._duty = self._clamp_duty(duty)
        if self._backend == "pigpio":
            if self._started:
                self._apply_pigpio_pwm()
        else:
            if self._started:
                self._apply_lgpio_pwm()

    def set_frequency(self, frequency):
        self._frequency = int(frequency)
        if self._backend == "pigpio":
            if self._started:
                self._apply_pigpio_pwm()
        else:
            if self._started:
                self._apply_lgpio_pwm()
        
    def stop(self):
        self._duty = 0.0
        if self._backend == "pigpio":
            try:
                self._pigpio_client.hardware_PWM(self._pin, 0, 0)
            except Exception:
                pass
            try:
                if self._pigpio_client is not None:
                    self._pigpio_client.stop()
                    self._pigpio_client = None
            except Exception:
                pass
        else:
            try:
                self._lgpio.tx_pwm(self._lgpio_handle, self._pin, 0, 0)
            except Exception:
                pass
            try:
                self._lgpio.gpio_write(self._lgpio_handle, self._pin, 0)
            except Exception:
                pass
            try:
                if self._lgpio_handle is not None:
                    self._lgpio.gpiochip_close(self._lgpio_handle)
                    self._lgpio_handle = None
            except Exception:
                pass
        self._started = False
        

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