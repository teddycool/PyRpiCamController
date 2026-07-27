# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import time
import threading
import signal
import sys
import os
from pathlib import Path

OTA_SHARED_DIR = Path('/home/pi/ota')
OTA_COMMAND_DIR = OTA_SHARED_DIR / 'commands'
CHECK_TRIGGER_FILE = OTA_COMMAND_DIR / 'ota_check_trigger'
APPLY_TRIGGER_FILE = OTA_COMMAND_DIR / 'ota_apply_trigger'

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from Settings.settings_manager import settings_manager
    from camcontroller_update_manager import UpdateManager
except ImportError as e:
    print(f"Could not import required modules: {e}")
    sys.exit(1)


class UpdateDaemon:
    """
    Background daemon that periodically checks for and applies OTA updates.
    
    This daemon:
    - Checks for updates at configured intervals
    - Only runs when OTA is enabled in settings
    - Handles graceful shutdown
    - Logs all activities
    - Can be controlled via systemd service
    """
    
    def __init__(self):
        self.update_manager = UpdateManager()
        self.logger = self.update_manager.logger
        self.running = False
        self.check_thread = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _ensure_command_dir(self):
        """Ensure the shared OTA command directory exists."""
        OTA_COMMAND_DIR.mkdir(parents=True, exist_ok=True)

    def _set_runtime_setting(self, path, value):
        """Persist OTA runtime state, including readonly status fields."""
        settings_manager.set(path, value, save=True, allow_readonly=True)

    def _set_last_check(self):
        """Persist the current OTA last-check timestamp."""
        self._set_runtime_setting('OTA.last_check', time.strftime('%Y-%m-%d %H:%M:%S'))
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down update daemon")
        self.stop()
        
    def start(self):
        """Start the update daemon."""
        if self.running:
            self.logger.warning("Update daemon is already running")
            return
        
        self.logger.info("Starting update daemon")
        
        # Initialize current version in settings
        self._update_current_version()
        
        self.running = True
        
        # Start background thread
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _update_current_version(self):
        """Update the current version in settings from VERSION file."""
        try:
            version_file = Path(__file__).parent.parent / 'VERSION'
            if version_file.exists():
                with open(version_file, 'r') as f:
                    current_version = f.read().strip()
                self._set_runtime_setting('OTA.current_version', current_version)
                self.logger.info(f"Current version set to: {current_version}")
            else:
                self.logger.warning("VERSION file not found")
        except Exception as e:
            self.logger.error(f"Failed to read VERSION file: {e}")
            
    def stop(self):
        """Stop the update daemon."""
        if not self.running:
            return
            
        self.logger.info("Stopping update daemon")
        self.running = False
        
        if self.check_thread and self.check_thread.is_alive():
            self.check_thread.join(timeout=5)
            
    def _check_loop(self):
        """Main loop that periodically checks for updates."""
        self.logger.info("Update check loop started")
        
        while self.running:
            try:
                # Check for manual triggers first
                self._check_manual_triggers()
                
                # Check if OTA is enabled for automatic checks
                if not settings_manager.get('OtaEnable'):
                    self.logger.debug("OTA is disabled, skipping automatic check")
                    time.sleep(60)  # Check every minute if enabled
                    continue
                
                # Check if auto-apply is disabled (manual mode)
                auto_apply = settings_manager.get('OTA.auto_apply')
                
                # Get check interval
                interval = settings_manager.get('OTA.check_interval')
                
                self.logger.info("Checking for OTA updates...")
                self._set_runtime_setting('OTA.update_status', 'checking')
                
                # Check for updates
                try:
                    if auto_apply:
                        # Old behavior: check and apply automatically
                        success = self.update_manager.perform_update()
                        if success is True:
                            self.logger.info("OTA check and update completed successfully")
                            self._update_current_version()
                            self._set_runtime_setting('OTA.available_version', '')
                            self._set_runtime_setting('OTA.update_status', 'idle')
                        elif success is False:
                            self.logger.warning("OTA update failed")
                            self._set_runtime_setting('OTA.update_status', 'error')
                        else:
                            # No updates available
                            self._set_runtime_setting('OTA.update_status', 'idle')
                    else:
                        # New behavior: check only, don't auto-apply
                        update_info = self.update_manager.check_for_updates()
                        if update_info:
                            available_version = update_info.get('version', 'Unknown')
                            self.logger.info(f"Update available: {available_version}")
                            self._set_runtime_setting('OTA.available_version', available_version)
                            self._set_runtime_setting('OTA.update_status', 'available')
                        else:
                            self.logger.info("No updates available")
                            self._set_runtime_setting('OTA.update_status', 'idle')
                    
                    # Update last check time
                    self._set_last_check()
                        
                except Exception as e:
                    self.logger.error(f"Error during OTA update: {e}")
                    self._set_runtime_setting('OTA.update_status', 'error')
                
                # Wait for next check
                self.logger.info(f"Next OTA check in {interval} seconds")
                
                # Sleep in small increments to allow for graceful shutdown
                # and prompt processing of manual trigger files.
                elapsed = 0
                while elapsed < interval and self.running:
                    step = min(10, interval - elapsed)
                    time.sleep(step)
                    elapsed += step

                    # Process manual check/apply requests promptly instead of
                    # waiting for the full check interval.
                    self._check_manual_triggers()
                    
            except Exception as e:
                self.logger.error(f"Error in OTA check loop: {e}")
                time.sleep(60)  # Wait before retrying
                
        self.logger.info("OTA check loop stopped")
    
    def _check_manual_triggers(self):
        """Check for manual trigger files and process them."""
        self._ensure_command_dir()
        check_trigger_file = CHECK_TRIGGER_FILE
        apply_trigger_file = APPLY_TRIGGER_FILE
        
        # Handle manual check trigger
        if check_trigger_file.exists():
            self.logger.info("Manual update check triggered via file")
            try:
                self._set_runtime_setting('OTA.update_status', 'checking')
                update_info = self.update_manager.check_for_updates()
                if update_info:
                    available_version = update_info.get('version', 'Unknown')
                    self.logger.info(f"Manual check found update: {available_version}")
                    self._set_runtime_setting('OTA.available_version', available_version)
                    self._set_runtime_setting('OTA.update_status', 'available')
                else:
                    self.logger.info("Manual check: No updates available")
                    self._set_runtime_setting('OTA.available_version', '')
                    self._set_runtime_setting('OTA.update_status', 'idle')
                
                self._set_last_check()
                
            except Exception as e:
                self.logger.error(f"Manual check failed: {e}")
                self._set_runtime_setting('OTA.update_status', 'error')
            finally:
                try:
                    check_trigger_file.unlink(missing_ok=True)
                except OSError:
                    pass
        
        # Handle manual apply trigger
        if apply_trigger_file.exists():
            self.logger.info("Manual update apply triggered via file")
            try:
                self._set_runtime_setting('OTA.update_status', 'applying')
                success = self.update_manager.perform_update()
                if success:
                    self.logger.info("Manual update application completed successfully")
                    self._update_current_version()
                    self._set_runtime_setting('OTA.available_version', '')
                    self._set_runtime_setting('OTA.update_status', 'idle')
                else:
                    self.logger.error("Manual update application failed")
                    self._set_runtime_setting('OTA.update_status', 'error')
                    
            except Exception as e:
                self.logger.error(f"Manual apply failed: {e}")
                self._set_runtime_setting('OTA.update_status', 'error')
            finally:
                try:
                    apply_trigger_file.unlink(missing_ok=True)
                except OSError:
                    pass
        
    def manual_check(self):
        """Manually trigger an OTA check (for testing or admin use)."""
        self.logger.info("Manual OTA check triggered")
        
        try:
            update_info = self.update_manager.check_for_updates()
            if update_info:
                available_version = update_info.get('version', 'Unknown')
                self._set_runtime_setting('OTA.available_version', available_version)
                self._set_runtime_setting('OTA.update_status', 'available')
                self._set_last_check()
                self.logger.info(f"Manual OTA check found update: {available_version}")
                return True
            else:
                self._set_runtime_setting('OTA.available_version', '')
                self._set_runtime_setting('OTA.update_status', 'idle')
                self._set_last_check()
                self.logger.info("Manual OTA check completed: no updates available")
                return True
        except Exception as e:
            self.logger.error(f"Error during manual OTA check: {e}")
            self._set_runtime_setting('OTA.update_status', 'error')
            return False


def main():
    """Main entry point for Update daemon."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update Daemon for PyRpiCamController')
    parser.add_argument('--manual', action='store_true', help='Perform manual update check and exit')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (default)')
    
    args = parser.parse_args()
    
    daemon = UpdateDaemon()
    
    if args.manual:
        # Manual mode - check once and exit
        print("Performing manual update check...")
        result = daemon.manual_check()
        sys.exit(0 if result else 1)
    else:
        # Daemon mode - run continuously
        try:
            daemon.start()
        except KeyboardInterrupt:
            print("Update daemon stopped by user")
        except Exception as e:
            print(f"Update daemon error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()