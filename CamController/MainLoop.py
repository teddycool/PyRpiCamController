# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

#Hardware config
from hwconfig import hwconfig1 as hwconfig

import logging
import os
from pathlib import Path
import subprocess
import shutil
import time
from typing import Any

import RPi.GPIO as GPIO

from CamStates import InitState
from CamStates import PostState
from CamStates import StreamState
from CamStates.state_names import StateName
from Connectivity import cpuserial
from IO import Display
from IO import Light
from IO import CpuTempMonitor
from IO import DS18B20TempMonitor
from Settings.settings_manager import settings_manager
import json
import MetricsLogger

logger = logging.getLogger("cam.mainloop")

#States: Init. Idle, Post, (ImageStream)


class _NoopDisplay:
    def startup(self):
        pass

    def off(self):
        pass

    def wifi_connected(self):
        pass

    def no_internet(self):
        pass

    def image_post(self):
        pass

class MainLoop:

    def __init__(self, settings: Any = None, hardware_config: dict[str, Any] | None = None):
        self._settings = settings or settings_manager
        self._hardware_config = hardware_config or hwconfig
        self._process_start_time = time.time()
        self._metrics_interval = max(5.0, float(self._settings.get("MetricsInterval", 30)))
        self._software_version = self._read_software_version()

        #TODO: add and check settings for IO enabled
        try:
            GPIO.setmode(GPIO.BCM)
            logger.info("GPIO initialized successfully")
        except Exception as e:
            logger.error(f"GPIO initialization failed: {e}")
            # Try to cleanup and retry
            try:
                GPIO.cleanup()
                GPIO.setmode(GPIO.BCM)
                logger.info("GPIO initialized successfully after cleanup")
            except Exception as e2:
                logger.error(f"GPIO initialization failed even after cleanup: {e2}")
                raise
                
        self.mycpuserial = cpuserial.getserial()
        logger.info("My serial is: %s", self.mycpuserial)

        self._lastconfigcheck = 0
        self._lasttempcheck = 0
        self._lastds18b20tempcheck = 0
        self._last_runtime_status_write = 0.0
        self._last_metrics_write = 0.0

        # Main-loop workload throttling
        self._runtime_status_interval = 0.5
        
        logger.info("Starting temperature monitor initialization...")
              
        self._cputempmonitor = CpuTempMonitor.CpuTempMonitor()
        self._cputemp = self._cputempmonitor.get_cpu_temperature()
        logger.info("CPU temperature monitor initialized: %s°C", self._cputemp)
        
        # Initialize DS18B20 temperature sensor if configured
        logger.info("Checking DS18B20 configuration...")
        ds18b20_pin = self._hardware_config["Io"].get("ds18b20pin")
        logger.info("DS18B20 pin from config: %s", ds18b20_pin)
        if ds18b20_pin is not None:
            try:
                logger.info("Attempting to initialize DS18B20 on pin %s...", ds18b20_pin)
                self._ds18b20tempmonitor = DS18B20TempMonitor.DS18B20TempMonitor(ds18b20_pin)
                self._ds18b20temp = self._ds18b20tempmonitor.get_temperature()
                logger.info("DS18B20 sensor initialized on pin %s, initial reading: %s", ds18b20_pin, self._ds18b20temp)
            except Exception as e:
                logger.error("Failed to initialize DS18B20 sensor: %s", str(e))
                self._ds18b20tempmonitor = None
                self._ds18b20temp = None
        else:
            logger.info("DS18B20 sensor not configured (pin is None)")
            self._ds18b20tempmonitor = None
            self._ds18b20temp = None

        
        # Setup IO, these settings are NOT configurable from backend but hardware dependent
        light_pin = self._hardware_config["Io"].get("lightcontrolgpio")
        display_pin = self._hardware_config["Io"].get("displaycontrolgpio")
        display_size = self._hardware_config["Io"].get("displaysize")

        pwm_channels = {
            0: {12, 18},
            1: {13, 19},
        }

        channel_conflict = (
            self._hardware_config["LightBox"]
            and light_pin is not None
            and display_pin is not None
            and any(light_pin in pins and display_pin in pins for pins in pwm_channels.values())
        )

        if channel_conflict:
            logger.warning(
                "PWM channel conflict detected (light GPIO %s, display GPIO %s). "
                "Prioritizing Light hardware PWM and disabling Display output.",
                light_pin,
                display_pin,
            )
            self._display = _NoopDisplay()
        elif display_pin is None or not display_size:
            logger.info(
                "Display not configured (gpio=%s, size=%s). Continuing without display.",
                display_pin,
                display_size,
            )
            self._display = _NoopDisplay()
        else:
            try:
                self._display = Display.Display(
                    display_pin,
                    display_size,
                )
                self._display.startup()
            except Exception as e:
                logger.error(
                    "Display initialization failed; continuing without display output: %s",
                    e,
                    exc_info=True,
                )
                self._display = _NoopDisplay()
        self._lightbox = None
     
        if self._hardware_config["LightBox"]:
            try:
                pwm_freq = self._settings.get("LightPwmFreq", 2500)
                self._lightbox = Light.Light(
                    GPIO,
                    light_pin,
                    pwm_freq,
                    allow_pigpio=True,
                )
                self._last_light_level = None  # Will be set in initialize()
                self._last_light_pwm_freq = pwm_freq
                logger.info("LightBox initialized")
            except Exception as e:
                self._lightbox = None
                self._last_light_level = None
                self._last_light_pwm_freq = None
                logger.error("LightBox initialization failed; continuing without light control: %s", e)
        else:
            self._last_light_level = None  # No lightbox available
            self._last_light_pwm_freq = None
        
        #Setup states
        self._initState = InitState.InitState()
        self._postState = PostState.PostState()
        self._streamState = StreamState.StreamState()
        
        self.states = {
            StateName.INIT: self._initState,
            StateName.STREAM: self._streamState,
            StateName.POST: self._postState,
        }

    def initialize(self):
        logger.info("Mainloop initialize")
        if self._lightbox is not None:
            light = self._settings.get("Light")
            self._lightbox.start(light)
            self._last_light_level = light  # Track current light level for dynamic updates
            self._last_light_pwm_freq = self._settings.get("LightPwmFreq", 2500)
            logger.info("Lightbox started with %s%%", light)
        elif self._hardware_config["LightBox"]:
            logger.warning("LightBox configured but unavailable due to backend initialization failure")
        
        # Check Mode setting to determine initial state
        mode = self._settings.get("Mode", "Cam")
        logger.info(f"Mode setting: {mode} - determining initial state")
        
        if mode == "Stream":
            logger.info("Starting in StreamState")
            self.set_state(StateName.STREAM)
        else:
            logger.info("Starting in InitState (camera mode)")
            self.set_state(StateName.INIT)

        self._emit_startup_metrics()
        
    def update(self):
        now = time.time()

        # Check for settings reload requests from web interface.
        self._check_settings_reload_request()
        
        #TODO: Check temperatures and other 'house-keeping'

        # Check CPU temperature
        if now - self._lasttempcheck > self._settings.get("CheckCpuTemp"):
            temp_reading = self._cputempmonitor.get_cpu_temperature()
            if temp_reading is not None:
                self._cputemp = temp_reading
                logger.debug("Current CPU-temperature: %s", str(self._cputemp))
                if self._cputemp > self._settings.get("Limits.maxcputemp"):
                    logger.error("Critical CPU-temperature: %s", str(self._cputemp))
                    logger.error("Will halt system for 5 minutes to cool off")
                    time.sleep(300)
                    logger.info("CPU-temperature after cool-off is now: %s", str(self._cputempmonitor.get_cpu_temperature()))
            else:
                logger.warning("Failed to read CPU temperature")
            self._lasttempcheck = now
        
        # Check DS18B20 temperature every 60 seconds
        if self._ds18b20tempmonitor is not None and now - self._lastds18b20tempcheck > 60:
            temp = self._ds18b20tempmonitor.get_temperature()
            if temp is not None:
                self._ds18b20temp = temp
                logger.debug("DS18B20 temperature: %.1f°C", temp)
            else:
                logger.warning("Failed to read DS18B20 temperature")
            self._lastds18b20tempcheck = now
            
        # Write runtime status with a generic loop interval.
        if now - self._last_runtime_status_write >= self._runtime_status_interval:
            self._update_runtime_status(now)
            self._last_runtime_status_write = now
        
        # Delegate state behavior to the active state implementation.
        self._currentstate.update(self)

        if now - self._last_metrics_write >= self._metrics_interval:
            self._emit_snapshot_metrics(now)
            self._last_metrics_write = now

    def _update_runtime_status(self, timestamp: float | None = None):
        """Write current runtime status to file for web interface"""
        try:
            awb_mode = str(self._settings.get("Cam.white_balance_mode", "auto") or "auto")
            awb_enable = bool(self._settings.get("Cam.awb_enable", True))
            awb_mode_display = awb_mode
            if not awb_enable:
                red_gain = self._settings.get("Cam.white_balance_red_gain", None)
                blue_gain = self._settings.get("Cam.white_balance_blue_gain", None)
                if red_gain is not None and blue_gain is not None:
                    try:
                        awb_mode_display = f"manual ({float(red_gain):.2f}/{float(blue_gain):.2f})"
                    except (TypeError, ValueError):
                        awb_mode_display = "manual"
                else:
                    awb_mode_display = "manual"

            status_data = {
                'timestamp': timestamp if timestamp is not None else time.time(),
                'cpu_temperature': self._cputemp if self._cputemp is not None else None,
                'ds18b20_temperature': self._ds18b20temp,
                'ds18b20_available': self._ds18b20tempmonitor is not None,
                'awb_mode': awb_mode,
                'awb_enable': awb_enable,
                'awb_mode_display': awb_mode_display,
            }

            current_state = getattr(self, '_currentstate', None)
            if current_state:
                try:
                    status_data.update(current_state.get_runtime_status())
                except Exception as e:
                    logger.debug("Failed to collect state runtime status: %s", e)
            
            status_file = "/tmp/cam_runtime_status.json"
            # Write to temporary file first, then rename for atomic operation
            temp_file = status_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(status_data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, status_file)
            parent_fd = os.open(os.path.dirname(status_file), os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
                
        except Exception as e:
            logger.debug("Failed to write runtime status: %s", str(e))      

    def _read_software_version(self) -> str:
        try:
            version_file = Path(__file__).resolve().parent.parent / "VERSION"
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.debug("Failed to read VERSION file: %s", e)
        return "unknown"

    def _read_throttled_state(self) -> str | None:
        try:
            result = subprocess.run(
                ["vcgencmd", "get_throttled"],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug("Failed to read throttled state: %s", e)
        return None

    def _collect_metrics_snapshot(self, timestamp: float | None = None) -> dict[str, Any]:
        timestamp = timestamp if timestamp is not None else time.time()

        load_1m = load_5m = load_15m = None
        try:
            load_1m, load_5m, load_15m = os.getloadavg()
        except Exception:
            pass

        cpu_count = os.cpu_count() or 1

        storage_total_bytes = None
        storage_free_bytes = None
        storage_used_bytes = None
        storage_path = None
        try:
            storage_location = self._settings.get('Cam.publishers.file.location')
            if not storage_location:
                storage_location = '/'

            usage_path = storage_location if os.path.isdir(storage_location) else os.path.dirname(storage_location) or '/'
            usage = shutil.disk_usage(usage_path)
            storage_total_bytes = usage.total
            storage_free_bytes = usage.free
            storage_used_bytes = usage.used
            storage_path = usage_path
        except Exception as e:
            logger.debug("Failed to collect storage metrics: %s", e)

        current_state = getattr(self, "_currentstate", None)
        state_metrics = {}
        if current_state is not None:
            try:
                state_metrics = current_state.get_metrics() if hasattr(current_state, "get_metrics") else {}
            except Exception as e:
                logger.debug("Failed to collect state metrics: %s", e)

        snapshot = {
            "sample_timestamp": timestamp,
            "software_version": self._software_version,
            "device_serial": self.mycpuserial,
            "mode": self._settings.get("Mode", "Cam"),
            "state": type(current_state).__name__ if current_state is not None else None,
            "uptime_seconds": round(timestamp - self._process_start_time, 1),
            "cpu_temperature": self._cputemp if self._cputemp is not None else None,
            "cpu_load": {
                "load_1m": load_1m,
                "load_5m": load_5m,
                "load_15m": load_15m,
                "load_per_cpu_1m": (load_1m / cpu_count) if load_1m is not None else None,
                "cpu_count": cpu_count,
            },
            "thermal": {
                "throttled": self._read_throttled_state(),
            },
            "sensors": {
                "ds18b20_available": self._ds18b20tempmonitor is not None,
                "environment_temperature": self._ds18b20temp,
            },
            "storage": {
                "path": storage_path,
                "total_bytes": storage_total_bytes,
                "free_bytes": storage_free_bytes,
                "used_bytes": storage_used_bytes,
            },
            "components": state_metrics,
        }

        return snapshot

    def _emit_startup_metrics(self) -> None:
        try:
            payload = self._collect_metrics_snapshot()
            payload.update({
                "metrics_interval_seconds": self._metrics_interval,
                "metrics_log_path": self._settings.get("MetricsLogFilePath", "/home/pi/shared/logs/cam-metrics.log"),
                "cpu_temp_check_interval_seconds": self._settings.get("CheckCpuTemp"),
            })
            MetricsLogger.emit_metrics("startup", data=payload)
            self._last_metrics_write = time.time()
        except Exception as e:
            logger.debug("Failed to emit startup metrics: %s", e)

    def _emit_snapshot_metrics(self, timestamp: float | None = None) -> None:
        try:
            MetricsLogger.emit_metrics("snapshot", data=self._collect_metrics_snapshot(timestamp))
        except Exception as e:
            logger.debug("Failed to emit snapshot metrics: %s", e)

    def _check_settings_reload_request(self):
        """Check for settings reload requests from web interface."""
        try:
            reload_file = "/tmp/cam_reload_settings.txt"
            if not os.path.exists(reload_file):
                return

            with open(reload_file, 'r') as f:
                reload_type = f.read().strip()

            # Remove request file immediately to avoid repeated processing.
            os.remove(reload_file)

            logger.info("Settings reload requested: %s", reload_type)

            if reload_type in ("restart_service", "reload_settings"):
                logger.info("Full service restart requested")
                os.system("sudo systemctl restart camcontroller.service")
            else:
                logger.warning("Unknown reload type: %s", reload_type)
        except Exception as e:
            logger.error("Error processing settings reload request: %s", e)

 
    def set_state(self, state_name: StateName | str):
        if isinstance(state_name, str):
            state_name = StateName(state_name)

        logger.info("Changing state to: %s", state_name.value)
        previous_state = getattr(self, "_currentstate", None)
        target_state = self.states[state_name]

        # Stop/cleanup previous state resources before switching.
        if previous_state is not None:
            try:
                previous_state.cleanup()
            except Exception as e:
                logger.warning("Failed to cleanup previous state cleanly: %s", e)

        # Merge hardware config with settings manager data
        settings_dict = dict(self._settings.get_dict())  # Convert SettingsDict to regular dict
        settings_dict.update(self._hardware_config)  # Add hardware configuration to settings

        try:
            target_state.initialize(settings_dict)
        except Exception:
            logger.exception("Failed to initialize state %s", state_name.value)
            fallback_state = previous_state
            if fallback_state is None and target_state is not self._initState:
                fallback_state = self._initState

            if fallback_state is not None and fallback_state is not target_state:
                try:
                    fallback_state.initialize(settings_dict)
                    self._currentstate = fallback_state
                    logger.warning(
                        "Restored state %s after %s initialization failed",
                        type(fallback_state).__name__,
                        state_name.value,
                    )
                except Exception:
                    logger.exception("Failed to restore previous state")
            raise

        self._currentstate = target_state
        logger.info("State changed to: %s", state_name.value)


    def stop(self):
        logger.info("Mainloop stopped")
        current_state = getattr(self, "_currentstate", None)
        if current_state is not None:
            try:
                current_state.dispose()
            except Exception:
                logger.exception("Failed to dispose active state")
        self._display.off()
        if self._lightbox is not None:
            logger.info("Lightbox stopped")
            self._lightbox.stop()
        try:
            GPIO.cleanup()
        except Exception:
            logger.exception("Failed to clean up GPIO")



if __name__ == '__main__':
    print ("Testcode for MainLoop")
    ml = MainLoop()
    ml.initialize()
    try:
        while(True):
            ml.update()
            time.sleep(0.5)
    except KeyboardInterrupt:
        ml.stop()
        print("Testcode ended...")
    except:
        pass
