# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import numpy as np
from typing import Dict, Any, Tuple
import logging
from ..ProcessorBase import ProcessorBase

logger = logging.getLogger("cam.vision.crop")

class CropProcessor(ProcessorBase):
    """
    Image cropping processor.
    
    Crops images to a specified rectangular region. Migrated from the original
    cropping logic in PostState.py to provide a reusable, configurable processor.
    """
    
    def __init__(self, name: str = "CropProcessor"):
        super().__init__(name)
        self._top_left = None
        self._bottom_right = None
        self._validate_coordinates = True
    
    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize crop processor with settings.
        
        Expected settings:
        - enabled: bool - whether cropping is enabled
        - top_left: [x, y] - top-left corner coordinates
        - bottom_right: [x, y] - bottom-right corner coordinates
        - validate_coordinates: bool - whether to validate crop area
        """
        super().initialize(settings)
        
        # Extract crop coordinates from settings
        self._top_left = self.get_setting('top_left', [300, 250])
        self._bottom_right = self.get_setting('bottom_right', [4301, 2351])
        self._validate_coordinates = self.get_setting('validate_coordinates', True)
        
        # Enable/disable based on settings
        if self.get_setting('enabled', True):
            self.enable()
        else:
            self.disable()
        
        logger.info(f"CropProcessor initialized: top_left={self._top_left}, bottom_right={self._bottom_right}")
    
    def process(self, image: np.ndarray, metadata: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Crop the input image to specified coordinates.
        
        Args:
            image: Input image as numpy array (BGR format)
            metadata: Current metadata dictionary
            
        Returns:
            Tuple of (cropped_image, updated_metadata)
        """
        if not self.validate_image(image):
            logger.warning("Invalid image input, returning original image")
            return image, metadata
        
        try:
            x1, y1 = self._top_left
            x2, y2 = self._bottom_right
            
            # Store original dimensions
            original_shape = image.shape
            self.add_metadata(metadata, 'original_shape', original_shape)
            self.add_metadata(metadata, 'crop_coordinates', {
                'top_left': [x1, y1],
                'bottom_right': [x2, y2]
            })
            
            # Validate crop coordinates if enabled
            if self._validate_coordinates:
                if not self._validate_crop_coordinates(image, x1, y1, x2, y2):
                    logger.warning("Invalid crop coordinates, returning original image")
                    self.add_metadata(metadata, 'crop_applied', False)
                    self.add_metadata(metadata, 'error', 'Invalid crop coordinates')
                    return image, metadata
            
            # Perform the crop - using numpy array slicing
            cropped_image = image[y1:y2, x1:x2]
            
            # Update metadata
            self.add_metadata(metadata, 'crop_applied', True)
            self.add_metadata(metadata, 'cropped_shape', cropped_image.shape)
            self.add_metadata(metadata, 'crop_reduction', {
                'width_reduction': original_shape[1] - cropped_image.shape[1],
                'height_reduction': original_shape[0] - cropped_image.shape[0],
                'area_reduction_percent': (1 - (cropped_image.shape[0] * cropped_image.shape[1]) / 
                                         (original_shape[0] * original_shape[1])) * 100
            })
            
            logger.debug(f"Image cropped from {original_shape} to {cropped_image.shape}")
            
            return cropped_image, metadata
            
        except Exception as e:
            logger.error(f"Error during image cropping: {e}", exc_info=True)
            self.add_metadata(metadata, 'crop_applied', False)
            self.add_metadata(metadata, 'error', str(e))
            return image, metadata
    
    def _validate_crop_coordinates(self, image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> bool:
        """
        Validate that crop coordinates are within image bounds and logical.
        
        Args:
            image: Input image
            x1, y1: Top-left coordinates
            x2, y2: Bottom-right coordinates
            
        Returns:
            True if coordinates are valid, False otherwise
        """
        height, width = image.shape[:2]
        
        # Check bounds
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            logger.warning(f"Crop coordinates out of bounds: ({x1},{y1})-({x2},{y2}) for image {width}x{height}")
            return False
        
        # Check logical order
        if x1 >= x2 or y1 >= y2:
            logger.warning(f"Invalid crop coordinates: top_left ({x1},{y1}) must be < bottom_right ({x2},{y2})")
            return False
        
        # Check minimum size (avoid crops that are too small)
        min_width, min_height = 10, 10  # Minimum crop size
        if (x2 - x1) < min_width or (y2 - y1) < min_height:
            logger.warning(f"Crop area too small: {x2-x1}x{y2-y1}, minimum is {min_width}x{min_height}")
            return False
        
        return True
    
    def update_crop_area(self, top_left: Tuple[int, int], bottom_right: Tuple[int, int]) -> None:
        """
        Update crop coordinates dynamically.
        
        Args:
            top_left: New top-left coordinates (x, y)
            bottom_right: New bottom-right coordinates (x, y)
        """
        self._top_left = list(top_left)
        self._bottom_right = list(bottom_right)
        logger.info(f"Updated crop area: {self._top_left} to {self._bottom_right}")
    
    def get_crop_area(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Get current crop coordinates.
        
        Returns:
            Tuple of (top_left, bottom_right) coordinates
        """
        return tuple(self._top_left), tuple(self._bottom_right)
    
    def calculate_crop_area_from_percentage(self, image: np.ndarray, 
                                          x_percent: float, y_percent: float, 
                                          width_percent: float, height_percent: float) -> None:
        """
        Set crop area based on percentage of image dimensions.
        
        Args:
            image: Reference image for calculating dimensions
            x_percent: X position as percentage (0.0-1.0)
            y_percent: Y position as percentage (0.0-1.0)
            width_percent: Width as percentage (0.0-1.0)
            height_percent: Height as percentage (0.0-1.0)
        """
        height, width = image.shape[:2]
        
        x1 = int(width * x_percent)
        y1 = int(height * y_percent)
        x2 = int(x1 + width * width_percent)
        y2 = int(y1 + height * height_percent)
        
        self.update_crop_area((x1, y1), (x2, y2))
        logger.info(f"Set crop area from percentages: {x_percent:.1%},{y_percent:.1%} + {width_percent:.1%}x{height_percent:.1%}")