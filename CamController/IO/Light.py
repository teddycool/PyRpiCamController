# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import logging
import os
import re
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("cam.light")


def _is_raspberry_pi_5() -> bool:
    model_path = Path("/proc/device-tree/model")
    try:
        model_text = model_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "Raspberry Pi 5" in model_text


class Light(object):
    def __init__(self, GPIO, pin, frequency=2500, allow_pigpio=True):
        self._gpio = GPIO
        self._pin = pin
        self._frequency = int(frequency)
        self._duty = 0.0
        self._started = False
        self._backend = None
        self._sysfs_pwmchip = None
        self._sysfs_pwm_channel = None
        self._pigpio = None
        self._pigpio_client = None
        self._lgpio = None
        self._lgpio_handle = None
        is_pi5 = _is_raspberry_pi_5()
        pigpio_error = None
        lgpio_error = None
        pi5_sysfs_error = None
        pi5_sysfs_enabled = os.getenv("PYCAM_PI5_SYSFS_PWM", "0") == "1"

        if is_pi5 and pi5_sysfs_enabled:
            try:
                self._init_pi5_sysfs_hwpwm()
                self._backend = "pi5-sysfs-hwpwm"
                logger.info("Light PWM backend: pi5-sysfs-hwpwm")
                return
            except Exception as e:
                pi5_sysfs_error = e
                logger.warning("Pi 5 hardware PWM backend unavailable: %s", e)
        elif is_pi5:
            logger.info(
                "Pi 5 sysfs hardware PWM backend is disabled by default. "
                "Set PYCAM_PI5_SYSFS_PWM=1 to enable once PWM overlay is confirmed."
            )

        # Prefer true hardware PWM via pigpio when available.
        if allow_pigpio and not is_pi5:
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
            if is_pi5:
                reason = f"kernel PWM init failed: {pi5_sysfs_error}" if pi5_sysfs_enabled else "sysfs PWM backend disabled (set PYCAM_PI5_SYSFS_PWM=1)"
                logger.warning(
                    "Pi 5 is using lgpio fallback for Light PWM (%s). This may flicker under CPU load.",
                    reason,
                )
            return
        except Exception as e:
            lgpio_error = e

        raise RuntimeError(
            "No supported hardware PWM backend available for Light. "
            f"pi5 sysfs error: {pi5_sysfs_error}; pigpio error: {pigpio_error}; "
            f"lgpio error: {lgpio_error}. "
            "RPi.GPIO software PWM fallback is disabled by design."
        )

    @staticmethod
    def _read_text(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    @staticmethod
    def _write_text(path, value):
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(value))

    def _init_pi5_sysfs_hwpwm(self):
        if self._pin not in {12, 13, 18, 19}:
            raise RuntimeError(f"GPIO {self._pin} does not support Pi 5 hardware PWM")

        channel = self._probe_pi5_pwm_channel()
        if channel is None:
            raise RuntimeError(f"Failed to switch GPIO {self._pin} to PWM0_CHANx via pinctrl")

        pwmchips = sorted(Path("/sys/class/pwm").glob("pwmchip*"))
        chosen_chip = None
        for chip in pwmchips:
            npwm_path = chip / "npwm"
            if not npwm_path.exists():
                continue
            try:
                npwm = int(self._read_text(npwm_path))
            except Exception:
                continue
            if channel < npwm:
                chosen_chip = chip
                break

        if chosen_chip is None:
            raise RuntimeError(f"No pwmchip provides channel {channel}")

        export_path = chosen_chip / "export"
        channel_dir = chosen_chip / f"pwm{channel}"

        if not channel_dir.exists():
            try:
                self._write_text(export_path, channel)
            except OSError:
                pass

            for _ in range(20):
                if channel_dir.exists():
                    break
                time.sleep(0.05)

        if not channel_dir.exists():
            raise RuntimeError(f"Failed to export PWM channel {channel} on {chosen_chip}")

        self._sysfs_pwmchip = chosen_chip
        self._sysfs_pwm_channel = channel

    def _probe_pi5_pwm_channel(self):
        for alt in range(8):
            set_result = subprocess.run(
                ["pinctrl", "set", str(self._pin), f"a{alt}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if set_result.returncode != 0:
                continue

            get_result = subprocess.run(
                ["pinctrl", "get", str(self._pin)],
                capture_output=True,
                text=True,
                check=False,
            )
            if get_result.returncode != 0:
                continue

            channel_match = re.search(r"PWM0_CHAN(\d+)", get_result.stdout)
            if channel_match:
                return int(channel_match.group(1))

        return None

    def _apply_sysfs_pwm(self):
        channel_dir = self._sysfs_pwmchip / f"pwm{self._sysfs_pwm_channel}"
        period_path = channel_dir / "period"
        duty_path = channel_dir / "duty_cycle"
        enable_path = channel_dir / "enable"

        frequency = max(1, int(self._frequency))
        period_ns = max(1, int(round(1_000_000_000 / frequency)))
        duty_ns = int(round(period_ns * (self._duty / 100.0)))
        duty_ns = max(0, min(period_ns, duty_ns))

        currently_enabled = self._read_text(enable_path) == "1"
        if currently_enabled:
            self._write_text(enable_path, 0)

        self._write_text(period_path, period_ns)
        self._write_text(duty_path, duty_ns)

        if duty_ns > 0:
            self._write_text(enable_path, 1)
        else:
            self._write_text(enable_path, 0)

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
        elif self._backend == "pi5-sysfs-hwpwm":
            self._apply_sysfs_pwm()
        else:
            self._apply_lgpio_pwm()
        self._started = True

    def set_duty(self, duty):
        self._duty = self._clamp_duty(duty)
        if self._started:
            if self._backend == "pigpio":
                self._apply_pigpio_pwm()
            elif self._backend == "pi5-sysfs-hwpwm":
                self._apply_sysfs_pwm()
            else:
                self._apply_lgpio_pwm()

    def set_frequency(self, frequency):
        self._frequency = int(frequency)
        if self._started:
            if self._backend == "pigpio":
                self._apply_pigpio_pwm()
            elif self._backend == "pi5-sysfs-hwpwm":
                self._apply_sysfs_pwm()
            else:
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
        elif self._backend == "pi5-sysfs-hwpwm":
            try:
                channel_dir = self._sysfs_pwmchip / f"pwm{self._sysfs_pwm_channel}"
                self._write_text(channel_dir / "enable", 0)
                self._write_text(channel_dir / "duty_cycle", 0)
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