# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import time
import logging
from .ProcessorBase import ProcessorBase

logger = logging.getLogger("cam.vision.pipeline")

class ImageProcessor:
    """
    Main image processing pipeline coordinator.
    
    Manages a chain of image processors that sequentially process images
    and accumulate metadata. Provides configuration, performance monitoring,
    and error handling for the entire pipeline.
    """
    
    def __init__(self):
        self._processors: List[ProcessorBase] = []
        self._statistics = {
            'total_processed': 0,
            'total_processing_time': 0.0,
            'processor_stats': {}
        }
        logger.info("ImageProcessor pipeline initialized")
    
    def add_processor(self, processor: ProcessorBase) -> None:
        """
        Add a processor to the pipeline.
        
        Args:
            processor: Processor instance to add
        """
        if not isinstance(processor, ProcessorBase):
            raise TypeError(f"Processor must inherit from ProcessorBase, got {type(processor)}")
        
        self._processors.append(processor)
        self._statistics['processor_stats'][processor.name] = {
            'processed_count': 0,
            'total_time': 0.0,
            'error_count': 0
        }
        logger.info(f"Added processor to pipeline: {processor}")
    
    def remove_processor(self, processor_name: str) -> bool:
        """
        Remove a processor from the pipeline.
        
        Args:
            processor_name: Name of processor to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, processor in enumerate(self._processors):
            if processor.name == processor_name:
                del self._processors[i]
                if processor_name in self._statistics['processor_stats']:
                    del self._statistics['processor_stats'][processor_name]
                logger.info(f"Removed processor from pipeline: {processor_name}")
                return True
        
        logger.warning(f"Processor not found for removal: {processor_name}")
        return False
    
    def get_processors(self) -> List[str]:
        """
        Get list of processor names in the pipeline.
        
        Returns:
            List of processor names in execution order
        """
        return [p.name for p in self._processors]
    
    def clear_processors(self) -> None:
        """Remove all processors from the pipeline."""
        self._processors.clear()
        self._statistics['processor_stats'].clear()
        logger.info("Cleared all processors from pipeline")
    
    def process(self, image: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process an image through the entire pipeline.
        
        Args:
            image: Input image as numpy array (BGR format)
            metadata: Optional initial metadata dictionary
            
        Returns:
            Tuple of (processed_image, final_metadata)
        """
        start_time = time.time()
        
        if metadata is None:
            metadata = {}
        
        # Initialize processing metadata
        if 'processing' not in metadata:
            metadata['processing'] = {
                'pipeline_start': time.time(),
                'processors_executed': [],
                'errors': []
            }
        
        current_image = image
        
        # Process through each enabled processor
        for processor in self._processors:
            if not processor.is_enabled():
                logger.debug(f"Skipping disabled processor: {processor.name}")
                continue
            
            try:
                processor_start = time.time()
                
                # Validate input before processing
                if not processor.validate_image(current_image):
                    error_msg = f"Invalid image input for processor {processor.name}"
                    logger.error(error_msg)
                    metadata['processing']['errors'].append(error_msg)
                    continue
                
                # Execute processor
                current_image, metadata = processor.process(current_image, metadata)
                
                # Update statistics
                processor_time = time.time() - processor_start
                stats = self._statistics['processor_stats'][processor.name]
                stats['processed_count'] += 1
                stats['total_time'] += processor_time
                
                metadata['processing']['processors_executed'].append({
                    'name': processor.name,
                    'execution_time': processor_time,
                    'timestamp': time.time()
                })
                
                logger.debug(f"Processed through {processor.name} in {processor_time:.3f}s")
                
            except Exception as e:
                error_msg = f"Error in processor {processor.name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # Update error statistics
                self._statistics['processor_stats'][processor.name]['error_count'] += 1
                metadata['processing']['errors'].append(error_msg)
                
                # Continue with next processor rather than failing entire pipeline
                continue
        
        # Finalize processing metadata
        total_time = time.time() - start_time
        metadata['processing']['pipeline_end'] = time.time()
        metadata['processing']['total_time'] = total_time
        
        # Update global statistics
        self._statistics['total_processed'] += 1
        self._statistics['total_processing_time'] += total_time
        
        logger.debug(f"Pipeline processing completed in {total_time:.3f}s")
        
        return current_image, metadata
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pipeline processing statistics.
        
        Returns:
            Dictionary containing performance and error statistics
        """
        stats = self._statistics.copy()
        
        # Calculate average processing time
        if stats['total_processed'] > 0:
            stats['average_processing_time'] = stats['total_processing_time'] / stats['total_processed']
        else:
            stats['average_processing_time'] = 0.0
        
        # Calculate processor-specific averages
        for processor_name, processor_stats in stats['processor_stats'].items():
            if processor_stats['processed_count'] > 0:
                processor_stats['average_time'] = processor_stats['total_time'] / processor_stats['processed_count']
            else:
                processor_stats['average_time'] = 0.0
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset all processing statistics."""
        self._statistics = {
            'total_processed': 0,
            'total_processing_time': 0.0,
            'processor_stats': {name: {'processed_count': 0, 'total_time': 0.0, 'error_count': 0} 
                               for name in self._statistics['processor_stats'].keys()}
        }
        logger.info("Reset pipeline statistics")
    
    def configure_from_settings(self, settings: Dict[str, Any]) -> None:
        """
        Configure processors from settings dictionary.
        
        Args:
            settings: Settings dictionary containing processor configurations
        """
        for processor in self._processors:
            # Look for processor-specific settings
            processor_settings = settings.get('Vision', {}).get('processors', {}).get(processor.name, {})
            
            if processor_settings:
                processor.initialize(processor_settings)
                
                # Handle enable/disable from settings
                if 'enabled' in processor_settings:
                    if processor_settings['enabled']:
                        processor.enable()
                    else:
                        processor.disable()
        
        logger.info(f"Configured {len(self._processors)} processors from settings")
    
    def __len__(self) -> int:
        """Return number of processors in pipeline."""
        return len(self._processors)
    
    def __repr__(self) -> str:
        """String representation of pipeline."""
        processor_names = [p.name for p in self._processors]
        return f"ImageProcessor(processors={processor_names})"