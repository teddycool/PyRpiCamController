# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger("cam.vision.processor")

class ProcessorBase(ABC):
    """
    Abstract base class for all image processing components.
    
    Each processor takes an image and metadata, performs specific processing,
    and returns the processed image and updated metadata.
    """
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.enabled = True
        self._settings = {}
        logger.debug(f"Initialized processor: {self.name}")
    
    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the processor with settings.
        
        Args:
            settings: Configuration dictionary for this processor
        """
        self._settings = settings
        logger.info(f"Processor {self.name} initialized with settings: {settings}")
    
    @abstractmethod
    def process(self, image: np.ndarray, metadata: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process an image and update metadata.
        
        Args:
            image: Input image as numpy array (BGR format from OpenCV)
            metadata: Current metadata dictionary
            
        Returns:
            Tuple of (processed_image, updated_metadata)
        """
        pass
    
    def enable(self) -> None:
        """Enable this processor."""
        self.enabled = True
        logger.debug(f"Processor {self.name} enabled")
    
    def disable(self) -> None:
        """Disable this processor."""
        self.enabled = False
        logger.debug(f"Processor {self.name} disabled")
    
    def is_enabled(self) -> bool:
        """Check if processor is enabled."""
        return self.enabled
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value with optional default.
        
        Args:
            key: Setting key (can use dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        try:
            keys = key.split('.')
            value = self._settings
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def validate_image(self, image: np.ndarray) -> bool:
        """
        Validate that image is in expected format.
        
        Args:
            image: Image array to validate
            
        Returns:
            True if valid, False otherwise
        """
        if image is None:
            logger.warning(f"Processor {self.name}: Image is None")
            return False
        
        if not isinstance(image, np.ndarray):
            logger.warning(f"Processor {self.name}: Image is not numpy array")
            return False
        
        if len(image.shape) != 3 or image.shape[2] != 3:
            logger.warning(f"Processor {self.name}: Image shape {image.shape} is not valid BGR format")
            return False
        
        return True
    
    def add_metadata(self, metadata: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """
        Helper method to safely add metadata.
        
        Args:
            metadata: Current metadata dictionary
            key: Key to add
            value: Value to add
            
        Returns:
            Updated metadata dictionary
        """
        if metadata is None:
            metadata = {}
        
        # Create processor-specific section if it doesn't exist
        processor_key = f"processors.{self.name}"
        if "processors" not in metadata:
            metadata["processors"] = {}
        if self.name not in metadata["processors"]:
            metadata["processors"][self.name] = {}
        
        metadata["processors"][self.name][key] = value
        logger.debug(f"Added metadata {processor_key}.{key} = {value}")
        
        return metadata
    
    def __repr__(self) -> str:
        """String representation of processor."""
        status = "enabled" if self.enabled else "disabled"
        return f"{self.__class__.__name__}(name='{self.name}', {status})"