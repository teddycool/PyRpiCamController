# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import numpy as np
import cv2
from typing import Dict, Any, Tuple
import logging
from ..ProcessorBase import ProcessorBase

logger = logging.getLogger("cam.vision.motion")

class MotionDetectionProcessor(ProcessorBase):
    """
    Motion detection processor using background subtraction.
    
    Enhanced version of the original MotionDetector with processor interface.
    Uses OpenCV background subtraction to detect motion in images.
    """
    
    def __init__(self, name: str = "MotionDetectionProcessor"):
        super().__init__(name)
        self._bg_subtractor = None
        self._motion_threshold = 200
        self._history = 50
        self._motion_detected = False
        self._diff_count = (0, 0)
        self._frame_count = 0
    
    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize motion detector with settings.
        
        Expected settings:
        - enabled: bool - whether motion detection is enabled
        - motion_threshold: int - minimum changed pixels for motion detection
        - history: int - number of background frames to maintain
        - learning_rate: float - background learning rate (default: -1 for automatic)
        """
        super().initialize(settings)
        
        # Extract motion detection settings
        self._motion_threshold = self.get_setting('motion_threshold', 200)
        self._history = self.get_setting('history', 50)
        learning_rate = self.get_setting('learning_rate', -1)
        
        # Initialize background subtractor
        try:
            # Try to use the newer createBackgroundSubtractorMOG2 if available
            self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=self._history,
                detectShadows=True
            )
            logger.info("Using BackgroundSubtractorMOG2 for motion detection")
        except AttributeError:
            try:
                # Fallback to older MOG if MOG2 not available
                self._bg_subtractor = cv2.bgsegm.createBackgroundSubtractorMOG(
                    history=self._history
                )
                logger.info("Using BackgroundSubtractorMOG for motion detection")
            except Exception as e:
                logger.error(f"Failed to initialize background subtractor: {e}")
                self.disable()
                return
        
        # Enable/disable based on settings
        if self.get_setting('enabled', False):
            self.enable()
        else:
            self.disable()
        
        logger.info(f"Motion detection initialized: threshold={self._motion_threshold}, history={self._history}")
    
    def process(self, image: np.ndarray, metadata: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process image for motion detection.
        
        Args:
            image: Input image as numpy array (BGR format)
            metadata: Current metadata dictionary
            
        Returns:
            Tuple of (original_image, updated_metadata_with_motion_info)
        """
        if not self.validate_image(image):
            logger.warning("Invalid image input for motion detection")
            return image, metadata
        
        if self._bg_subtractor is None:
            logger.warning("Background subtractor not initialized")
            self.add_metadata(metadata, 'motion_detected', False)
            self.add_metadata(metadata, 'error', 'Background subtractor not initialized')
            return image, metadata
        
        try:
            # Convert to grayscale for motion detection
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply background subtraction
            motion_mask = self._bg_subtractor.apply(gray_image)
            
            # Calculate motion metrics
            total_pixels = motion_mask.size
            changed_pixels = len(motion_mask[motion_mask > 254])  # Count white pixels (motion)
            self._diff_count = (total_pixels, changed_pixels)
            
            # Determine if motion is detected
            self._motion_detected = changed_pixels > self._motion_threshold
            self._frame_count += 1
            
            # Calculate motion percentage
            motion_percentage = (changed_pixels / total_pixels) * 100 if total_pixels > 0 else 0
            
            # Add motion information to metadata
            motion_info = {
                'motion_detected': self._motion_detected,
                'changed_pixels': changed_pixels,
                'total_pixels': total_pixels,
                'motion_percentage': round(motion_percentage, 2),
                'threshold': self._motion_threshold,
                'frame_count': self._frame_count
            }
            
            self.add_metadata(metadata, 'motion_analysis', motion_info)
            
            # Add motion mask to metadata for potential debugging/visualization
            if self.get_setting('include_motion_mask', False):
                self.add_metadata(metadata, 'motion_mask', motion_mask)
            
            # Calculate motion areas (contours) if enabled
            if self.get_setting('detect_motion_areas', True) and self._motion_detected:
                motion_areas = self._find_motion_areas(motion_mask)
                self.add_metadata(metadata, 'motion_areas', motion_areas)
            
            logger.debug(f"Motion detection: {changed_pixels} pixels changed, motion={self._motion_detected}")
            
            return image, metadata
            
        except Exception as e:
            logger.error(f"Error during motion detection: {e}", exc_info=True)
            self.add_metadata(metadata, 'motion_detected', False)
            self.add_metadata(metadata, 'error', str(e))
            return image, metadata
    
    def _find_motion_areas(self, motion_mask: np.ndarray) -> list:
        """
        Find contours of motion areas in the motion mask.
        
        Args:
            motion_mask: Binary motion mask from background subtraction
            
        Returns:
            List of motion area dictionaries with position and size info
        """
        try:
            # Find contours in the motion mask
            contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            motion_areas = []
            min_area = self.get_setting('min_motion_area', 100)  # Minimum area to consider as motion
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                
                if area < min_area:
                    continue  # Skip small motion areas
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate center point
                center_x = x + w // 2
                center_y = y + h // 2
                
                motion_area = {
                    'id': i,
                    'area': int(area),
                    'bounding_box': {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)},
                    'center': {'x': int(center_x), 'y': int(center_y)}
                }
                
                motion_areas.append(motion_area)
            
            return motion_areas
            
        except Exception as e:
            logger.error(f"Error finding motion areas: {e}")
            return []
    
    def reset_background(self) -> None:
        """
        Reset the background model.
        Useful when camera position changes or lighting conditions change significantly.
        """
        if self._bg_subtractor is not None:
            # For MOG2, we need to recreate the subtractor to reset
            try:
                self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                    history=self._history,
                    detectShadows=True
                )
                logger.info("Background model reset (MOG2)")
            except AttributeError:
                self._bg_subtractor = cv2.bgsegm.createBackgroundSubtractorMOG(
                    history=self._history
                )
                logger.info("Background model reset (MOG)")
            
            self._frame_count = 0
    
    def get_motion_status(self) -> Dict[str, Any]:
        """
        Get current motion detection status.
        
        Returns:
            Dictionary with current motion detection state
        """
        return {
            'motion_detected': self._motion_detected,
            'last_diff_count': self._diff_count,
            'threshold': self._motion_threshold,
            'frame_count': self._frame_count,
            'enabled': self.is_enabled()
        }
    
    def update_threshold(self, new_threshold: int) -> None:
        """
        Update motion detection threshold.
        
        Args:
            new_threshold: New pixel count threshold for motion detection
        """
        old_threshold = self._motion_threshold
        self._motion_threshold = max(1, new_threshold)  # Ensure positive threshold
        logger.info(f"Motion threshold updated: {old_threshold} -> {self._motion_threshold}")
    
    def create_annotated_image(self, image: np.ndarray, motion_areas: list) -> np.ndarray:
        """
        Create an annotated version of the image with motion areas highlighted.
        
        Args:
            image: Original image
            motion_areas: List of motion areas from motion detection
            
        Returns:
            Annotated image with motion areas drawn
        """
        annotated = image.copy()
        
        for area in motion_areas:
            bbox = area['bounding_box']
            center = area['center']
            
            # Draw bounding rectangle
            cv2.rectangle(annotated, 
                         (bbox['x'], bbox['y']), 
                         (bbox['x'] + bbox['width'], bbox['y'] + bbox['height']),
                         (0, 255, 0), 2)  # Green rectangle
            
            # Draw center point
            cv2.circle(annotated, (center['x'], center['y']), 5, (0, 0, 255), -1)  # Red center
            
            # Add area size text
            cv2.putText(annotated, f"Area: {area['area']}", 
                       (bbox['x'], bbox['y'] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return annotated