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
                # Check if OTA is enabled
                if not settings_manager.get('OtaEnable', False):
                    self.logger.debug("OTA is disabled, skipping check")
                    time.sleep(60)  # Check every minute if enabled
                    continue
                
                # Get check interval
                interval = settings_manager.get('OTA.check_interval', 3600)
                
                self.logger.info("Checking for OTA updates...")
                
                # Check for updates (this will download and install if available)
                try:
                    success = self.ota_manager.perform_update()
                    if success is True:
                        self.logger.info("OTA check completed successfully")
                    elif success is False:
                        self.logger.warning("OTA update failed")
                    # success could also be None if no updates available
                        
                except Exception as e:
                    self.logger.error(f"Error during OTA update: {e}")
                
                # Wait for next check
                self.logger.info(f"Next OTA check in {interval} seconds")
                
                # Sleep in small increments to allow for graceful shutdown
                elapsed = 0
                while elapsed < interval and self.running:
                    time.sleep(min(10, interval - elapsed))
                    elapsed += 10
                    
            except Exception as e:
                self.logger.error(f"Error in OTA check loop: {e}")
                time.sleep(60)  # Wait before retrying
                
        self.logger.info("OTA check loop stopped")
        
    def manual_check(self):
        """Manually trigger an OTA check (for testing or admin use)."""
        self.logger.info("Manual OTA check triggered")
        
        try:
            result = self.ota_manager.perform_update()
            if result:
                self.logger.info("Manual OTA check completed successfully")
            else:
                self.logger.warning("Manual OTA check failed")
            return result
        except Exception as e:
            self.logger.error(f"Error during manual OTA check: {e}")
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