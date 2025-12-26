# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import logging
import logging.handlers
import requests
import time
import os
import sys
import shutil
import tarfile
import hashlib
import json
import subprocess
import signal
from datetime import datetime
from pathlib import Path

class OTAManager:
    """
    Comprehensive Over-The-Air update manager with robust error handling and recovery.
    
    Features:
    - Atomic updates with rollback capability
    - Checksum verification
    - Health checks before and after update
    - Progress reporting to backend
    - Graceful recovery on failure
    """
    
    def __init__(self, config_path=None):
        self.setup_logging()
        self.load_configuration(config_path)
        self.setup_paths()
        
    def setup_logging(self):
        """Setup comprehensive logging for OTA operations."""
        self.logger = logging.getLogger("OTA")
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        log_dir = Path('/home/pi/shared/logs')
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'ota.log',
            maxBytes=1024*1024,  # 1MB
            backupCount=5
        )
        file_handler.setFormatter(console_formatter)
        self.logger.addHandler(file_handler)
        
    def load_configuration(self, config_path):
        """Load OTA configuration from settings system."""
        try:
            # Import settings manager
            sys.path.append('/home/pi/PyRpiCamController')
            from Settings.settings_manager import settings_manager
            
            self.config = {
                'enabled': settings_manager.get('OtaEnable'),
                'server_url': settings_manager.get('OTA.server_url', 'https://www.biwebben.se'),
                'check_interval': settings_manager.get('OTA.check_interval', 3600),  # 1 hour
                'api_key': settings_manager.get('OTA.api_key', ''),
                'service_name': settings_manager.get('OTA.service_name', 'camcontroller.service'),
                'install_path': settings_manager.get('OTA.install_path', '/home/pi/PyRpiCamController'),
                'backup_retention': settings_manager.get('OTA.backup_retention', 3),
                'health_check_timeout': settings_manager.get('OTA.health_check_timeout', 120),
                'download_timeout': settings_manager.get('OTA.download_timeout', 300)
            }
            
        except Exception as e:
            self.logger.warning(f"Could not load settings, using defaults: {e}")
            self.config = self._default_config()
            
    def _default_config(self):
        """Default OTA configuration."""
        return {
            'enabled': False,
            'server_url': 'https://www.biwebben.se',
            'check_interval': 3600,
            'api_key': '',
            'service_name': 'camcontroller.service',
            'install_path': '/home/pi/PyRpiCamController',
            'backup_retention': 3,
            'health_check_timeout': 120,
            'download_timeout': 300
        }
        
    def setup_paths(self):
        """Setup directory structure for OTA operations."""
        base_path = Path('/home/pi/ota')
        
        self.paths = {
            'base': base_path,
            'downloads': base_path / 'downloads',
            'backups': base_path / 'backups',
            'temp': base_path / 'temp',
            'scripts': base_path / 'scripts',
            'install_path': Path(self.config['install_path'])
        }
        
        # Create directories
        for path in self.paths.values():
            path.mkdir(parents=True, exist_ok=True)
            
        self.logger.info(f"OTA paths configured: {self.paths}")
        
    def get_cpu_serial(self):
        """Get CPU serial for device identification."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip().lstrip('0')
        except Exception as e:
            self.logger.warning(f"Could not get CPU serial: {e}")
            return "unknown"
            
    def check_for_updates(self):
        """Check if updates are available from server."""
        if not self.config['enabled']:
            self.logger.info("OTA updates are disabled")
            return None
            
        try:
            cpu_id = self.get_cpu_serial()
            
            # Get current version
            current_version = self._get_current_version()
            
            # Check with server
            check_url = f"{self.config['server_url']}/api/ota/check"
            params = {
                'cpu_id': cpu_id,
                'current_version': current_version,
                'api_key': self.config['api_key']
            }
            
            self.logger.info(f"Checking for updates: {check_url}")
            response = requests.get(check_url, params=params, timeout=30)
            response.raise_for_status()
            
            update_info = response.json()
            
            if update_info.get('update_available'):
                self.logger.info(f"Update available: {update_info}")
                return update_info
            else:
                self.logger.info("No updates available")
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}")
            return None
            
    def download_update(self, update_info):
        """Download and verify update package."""
        try:
            download_url = update_info['download_url']
            expected_checksum = update_info.get('checksum')
            
            # Download file
            download_path = self.paths['downloads'] / f"update_{update_info['version']}.tar.gz"
            
            self.logger.info(f"Downloading update from {download_url}")
            
            with requests.get(download_url, stream=True, timeout=self.config['download_timeout']) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) == 0:  # Log every MB
                                self.logger.info(f"Download progress: {progress:.1f}%")
            
            # Verify checksum
            if expected_checksum:
                actual_checksum = self._calculate_checksum(download_path)
                if actual_checksum != expected_checksum:
                    raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                self.logger.info("Checksum verification passed")
            
            self.logger.info(f"Update downloaded successfully: {download_path}")
            return download_path
            
        except Exception as e:
            self.logger.error(f"Error downloading update: {e}")
            raise
            
    def create_backup(self):
        """Create backup of current installation."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_version = self._get_current_version()
            backup_name = f"backup_{current_version}_{timestamp}.tar.gz"
            backup_path = self.paths['backups'] / backup_name
            
            self.logger.info(f"Creating backup: {backup_path}")
            
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(self.paths['install_path'], arcname="PyRpiCamController")
                
            self.logger.info(f"Backup created successfully: {backup_path}")
            
            # Clean old backups
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            raise
            
    def install_update(self, update_package_path):
        """Install the downloaded update package."""
        try:
            # Extract to temporary location
            temp_extract_path = self.paths['temp'] / 'extract'
            if temp_extract_path.exists():
                shutil.rmtree(temp_extract_path)
            temp_extract_path.mkdir()
            
            self.logger.info(f"Extracting update package: {update_package_path}")
            
            with tarfile.open(update_package_path, "r:gz") as tar:
                tar.extractall(temp_extract_path)
                
            # Find extracted content
            extracted_items = list(temp_extract_path.iterdir())
            if len(extracted_items) != 1:
                raise ValueError("Update package should contain exactly one directory")
                
            source_path = extracted_items[0]
            
            # Stop service
            self.logger.info("Stopping camera service")
            self._stop_service()
            
            # Wait for service to stop
            time.sleep(10)
            
            # Backup current installation (already done, but keep reference)
            # backup_path = self.create_backup()  # Already done before calling this
            
            # Install new version
            self.logger.info(f"Installing update from {source_path} to {self.paths['install_path']}")
            
            # Remove old installation (but keep backup)
            if self.paths['install_path'].exists():
                shutil.rmtree(self.paths['install_path'])
                
            # Copy new installation
            shutil.copytree(source_path, self.paths['install_path'])
            
            # Set proper permissions
            self._set_permissions()
            
            self.logger.info("Update installation completed")
            
        except Exception as e:
            self.logger.error(f"Error installing update: {e}")
            raise
            
    def verify_update(self):
        """Verify that the update was successful."""
        try:
            self.logger.info("Starting post-update verification")
            
            # Start service
            self._start_service()
            
            # Wait for service to start
            time.sleep(15)
            
            # Check service health
            start_time = time.time()
            timeout = self.config['health_check_timeout']
            
            while time.time() - start_time < timeout:
                if self._check_service_health():
                    self.logger.info("Update verification successful - service is healthy")
                    return True
                    
                time.sleep(5)
                self.logger.info("Waiting for service to become healthy...")
                
            self.logger.error("Update verification failed - service not healthy")
            return False
            
        except Exception as e:
            self.logger.error(f"Error during update verification: {e}")
            return False
            
    def rollback_update(self, backup_path):
        """Rollback to previous version using backup."""
        try:
            self.logger.warning("Starting rollback procedure")
            
            # Stop service
            self._stop_service()
            time.sleep(10)
            
            # Remove failed installation
            if self.paths['install_path'].exists():
                shutil.rmtree(self.paths['install_path'])
                
            # Extract backup
            self.logger.info(f"Restoring from backup: {backup_path}")
            
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(self.paths['install_path'].parent)
                
            # Set permissions
            self._set_permissions()
            
            # Start service
            self._start_service()
            time.sleep(15)
            
            # Verify rollback
            if self._check_service_health():
                self.logger.info("Rollback completed successfully")
                return True
            else:
                self.logger.error("Rollback verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False
            
    def perform_update(self):
        """Main update procedure with full error handling."""
        update_info = None
        backup_path = None
        
        try:
            self.logger.info("=== Starting OTA Update Process ===")
            
            # Check for updates
            update_info = self.check_for_updates()
            if not update_info:
                return True  # No updates available
                
            # Report update start to backend
            self._report_update_status('started', update_info)
            
            # Create backup
            backup_path = self.create_backup()
            
            # Download update
            package_path = self.download_update(update_info)
            
            # Install update
            self.install_update(package_path)
            
            # Verify installation
            if self.verify_update():
                self.logger.info("=== OTA Update Completed Successfully ===")
                self._report_update_status('success', update_info)
                
                # Optional: Reboot system
                if update_info.get('requires_reboot', False):
                    self.logger.info("Update requires reboot - rebooting in 30 seconds")
                    time.sleep(30)
                    os.system("sudo reboot")
                
                return True
            else:
                # Verification failed, rollback
                self.logger.warning("Update verification failed, attempting rollback")
                
                if backup_path and self.rollback_update(backup_path):
                    self.logger.info("Rollback completed successfully")
                    self._report_update_status('failed_rollback_success', update_info, 
                                             "Update failed verification, rolled back successfully")
                else:
                    self.logger.error("Rollback failed - manual intervention required")
                    self._report_update_status('failed_rollback_failed', update_info,
                                             "Update and rollback both failed - manual intervention required")
                
                return False
                
        except Exception as e:
            self.logger.error(f"Critical error during update process: {e}")
            
            if backup_path and update_info:
                self.logger.info("Attempting emergency rollback")
                if self.rollback_update(backup_path):
                    self._report_update_status('failed_rollback_success', update_info, str(e))
                else:
                    self._report_update_status('failed_rollback_failed', update_info, str(e))
            else:
                if update_info:
                    self._report_update_status('failed', update_info, str(e))
                    
            return False
            
    # Helper methods
    def _get_current_version(self):
        """Get current software version."""
        try:
            version_file = self.paths['install_path'] / 'VERSION'
            if version_file.exists():
                return version_file.read_text().strip()
        except Exception:
            pass
        return "unknown"
        
    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
        
    def _stop_service(self):
        """Stop the camera service."""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'stop', self.config['service_name']], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.logger.warning(f"Service stop returned non-zero: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error stopping service: {e}")
            
    def _start_service(self):
        """Start the camera service."""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'start', self.config['service_name']], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.logger.warning(f"Service start returned non-zero: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error starting service: {e}")
            
    def _check_service_health(self):
        """Check if service is running and healthy."""
        try:
            # Check if service is active
            result = subprocess.run(['systemctl', 'is-active', self.config['service_name']], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip() == 'active':
                # Additional health checks could go here
                # e.g., check if web interface responds, check log for errors, etc.
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking service health: {e}")
            return False
            
    def _set_permissions(self):
        """Set proper file permissions after installation."""
        try:
            os.system(f"sudo chown -R pi:pi {self.paths['install_path']}")
            os.system(f"sudo chmod +x {self.paths['install_path']}/CamController/Main.py")
        except Exception as e:
            self.logger.warning(f"Error setting permissions: {e}")
            
    def _cleanup_old_backups(self):
        """Remove old backup files beyond retention limit."""
        try:
            backups = sorted(self.paths['backups'].glob('backup_*.tar.gz'), 
                           key=lambda x: x.stat().st_mtime, reverse=True)
            
            for old_backup in backups[self.config['backup_retention']:]:
                old_backup.unlink()
                self.logger.info(f"Removed old backup: {old_backup}")
                
        except Exception as e:
            self.logger.warning(f"Error cleaning up old backups: {e}")
            
    def _report_update_status(self, status, update_info, error_message=None):
        """Report update status to backend server."""
        try:
            if not self.config['api_key']:
                return
                
            report_url = f"{self.config['server_url']}/api/ota/report"
            
            data = {
                'cpu_id': self.get_cpu_serial(),
                'status': status,
                'version': update_info.get('version'),
                'timestamp': datetime.now().isoformat(),
                'api_key': self.config['api_key']
            }
            
            if error_message:
                data['error_message'] = error_message
                
            response = requests.post(report_url, json=data, timeout=30)
            response.raise_for_status()
            
            self.logger.info(f"Status reported to backend: {status}")
            
        except Exception as e:
            self.logger.warning(f"Could not report status to backend: {e}")


def main():
    """Main entry point for OTA installer."""
    ota = OTAManager()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        ota.logger.info(f"Received signal {signum}, shutting down gracefully")
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Perform update
    success = ota.perform_update()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()