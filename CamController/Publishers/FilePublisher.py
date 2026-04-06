# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import os
import time
import logging
import shutil
import glob
from typing import Tuple, List

from .PublisherBase import PublisherBase
from Settings.settings_manager import settings_manager

logger = logging.getLogger("cam.publisher.file")

class FilePublisher(PublisherBase):
    def __init__(self):
        self.location = "/home/pi/shared/images/"
        self.img_format = "jpg"  # Default image format
        
        # Storage management settings
        self.storage_enabled = True
        self.storage_mode = "delete_old"  # "stop_saving" or "delete_old"
        self.threshold_value = 500
        self.threshold_unit = "MB"  # "MB" or "percent"
        
        logger.debug("Init FilePublisher")

    def initialize(self, settings):
        # Update location from settings if available
        self.location = settings.get("Cam", {}).get("publishers", {}).get("file", {}).get("location", self.location)
        os.makedirs(self.location, exist_ok=True)

        self.img_format = "jpg"
        
        # Initialize storage management settings
        storage_settings = settings.get("Cam", {}).get("storage_management", {})
        self.storage_enabled = storage_settings.get("enabled", self.storage_enabled)
        self.storage_mode = storage_settings.get("mode", self.storage_mode)
        self.threshold_value = storage_settings.get("threshold_value", self.threshold_value)
        self.threshold_unit = storage_settings.get("threshold_unit", self.threshold_unit)
        
        logger.info(f"FilePublisher initialized with location: {self.location}, format: {self.img_format}")
        logger.info(f"Storage management enabled: {self.storage_enabled}, mode: {self.storage_mode}, threshold: {self.threshold_value} {self.threshold_unit}")

    def get_disk_usage(self, path: str) -> Tuple[int, int, int]:
        """Get disk usage statistics for given path.
        
        Returns:
            Tuple of (total_bytes, used_bytes, free_bytes)
        """
        try:
            total, used, free = shutil.disk_usage(path)
            return total, used, free
        except Exception as e:
            logger.error(f"Failed to get disk usage for {path}: {e}")
            return 0, 0, 0

    def is_disk_space_low(self) -> bool:
        """Check if disk space is below threshold."""
        if not self.storage_enabled:
            return False
            
        total, used, free = self.get_disk_usage(self.location)
        
        if total == 0:  # Error getting disk usage
            return False
            
        if self.threshold_unit == "MB":
            threshold_bytes = self.threshold_value * 1024 * 1024
            return free < threshold_bytes
        elif self.threshold_unit == "percent":
            free_percent = (free / total) * 100
            return free_percent < self.threshold_value
        
        return False

    def get_old_files(self) -> List[Tuple[str, float]]:
        """Get list of old image and metadata files sorted by modification time.
        
        Returns:
            List of tuples (filepath, modification_time) sorted oldest first
        """
        files = []
        
        # Get all image files
        image_pattern = os.path.join(self.location, f"*.{self.img_format}")
        for img_file in glob.glob(image_pattern):
            try:
                mtime = os.path.getmtime(img_file)
                files.append((img_file, mtime))
                
                # Also add corresponding metadata file if exists
                base_name = os.path.splitext(img_file)[0]
                meta_file = f"{base_name}.json"
                if os.path.exists(meta_file):
                    files.append((meta_file, mtime))
            except OSError:
                continue
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x[1])
        return files

    def delete_old_files(self, target_free_mb: int = None) -> int:
        """Delete old files until enough space is available.
        
        Args:
            target_free_mb: Target free space in MB. If None, uses threshold + 100MB buffer
            
        Returns:
            Number of files deleted
        """
        if target_free_mb is None:
            target_free_mb = self.threshold_value + 100  # Add buffer
            
        deleted_count = 0
        old_files = self.get_old_files()
        
        for file_path, _ in old_files:
            if not self.is_disk_space_low():
                break
                
            try:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                deleted_count += 1
                logger.info(f"Deleted old file: {file_path} ({file_size / 1024 / 1024:.1f} MB)")
                
            except OSError as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
        
        return deleted_count

    def manage_storage_space(self) -> bool:
        """Manage storage space according to settings.
        
        Returns:
            True if sufficient space is available for saving, False otherwise
        """
        if not self.storage_enabled:
            return True
            
        if not self.is_disk_space_low():
            return True
            
        total, used, free = self.get_disk_usage(self.location)
        free_mb = free / (1024 * 1024)
        
        logger.warning(f"Low disk space detected. Free space: {free_mb:.1f} MB")
        
        if self.storage_mode == "stop_saving":
            logger.warning("Storage mode: stop_saving. Refusing to save new files.")
            return False
            
        elif self.storage_mode == "delete_old":
            logger.info("Storage mode: delete_old. Attempting to free space by deleting old files.")
            deleted_count = self.delete_old_files()
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old files to free space.")
                return not self.is_disk_space_low()  # Check if we freed enough space
            else:
                logger.error("No old files to delete, but disk space is still low.")
                return False
        
        return False

    def publish(self, jpgimagedata, metadata):
        try:
            # Keep runtime behavior in sync with latest persisted settings.
            try:
                settings_manager.load_user_settings()
            except Exception as e:
                logger.warning(f"Could not reload user settings before publish: {e}")

            # Check and manage storage space before saving
            if not self.manage_storage_space():
                logger.error("Cannot save image: insufficient disk space and unable to free space.")
                return
            
            timestamp = int(time.time())
            img_filename = os.path.join(self.location, f"{timestamp}.{self.img_format}")

            # Write image data to file
            with open(img_filename, "wb") as img_file:
                img_file.write(jpgimagedata.tobytes())
            logger.debug(f"Saved image to {img_filename}")
            
            # Log current disk usage periodically (every 10th save)
            if timestamp % 10 == 0:
                total, used, free = self.get_disk_usage(self.location)
                free_mb = free / (1024 * 1024)
                used_percent = (used / total) * 100
                logger.info(f"Disk usage: {used_percent:.1f}% used, {free_mb:.1f} MB free")
                
        except Exception as e:
            logger.error(f"FilePublisher failed to save image or metadata: {e}", exc_info=True)