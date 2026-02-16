# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
import time
import logging

# Import pipeline components only
from .pipeline.ImageProcessor import ImageProcessor
from .pipeline.processors.MotionDetectionProcessor import MotionDetectionProcessor
# ObjectDetectionProcessor imported dynamically when needed

logger = logging.getLogger("cam.vision.manager")


class VisionManager:
    """
    Vision Manager using pipeline-based processing system.
    
    Manages a configurable chain of vision processors (motion detection, 
    object detection, face recognition, etc.) with unified settings and 
    performance monitoring.
    """
    
    def __init__(self):
        """Initialize VisionManager with pipeline processing."""
        self._settings = {}
        self._initialized = False
        self._image_processor = None
        
        # Results from last processing
        self._last_results = {
            'motion_detected': False,
            'objects_detected': [],
            'faces_detected': [],
            'processing_time': 0.0,
            'metadata': {}
        }
        
        logger.info("VisionManager initialized with pipeline processing")
    
    def initialize(self, settings: Dict[str, Any]):
        """
        Initialize the vision pipeline with settings.
        
        Expected settings structure:
        {
            "Vision": {
                "enabled_processors": ["motion", "object", "face"],
                "processor_order": ["motion", "object", "face"],
                "performance_monitoring": true
            },
            "MotionDetector": { motion settings },
            "ObjectDetector": { object detection settings },
            "FaceRecognition": { face recognition settings }
        }
        """
        self._settings = settings
        vision_settings = settings.get("Vision", {})
        
        # Get enabled processors and their order
        enabled_processors = vision_settings.get("enabled_processors", ["motion"])
        processor_order = vision_settings.get("processor_order", enabled_processors)
        
        # Initialize pipeline
        self._image_processor = ImageProcessor()
        
        # Add processors in specified order
        for processor_name in processor_order:
            if processor_name not in enabled_processors:
                continue
                
            if processor_name == "motion":
                self._add_motion_processor(settings)
            elif processor_name == "object":
                self._add_object_processor(settings)
            elif processor_name == "face":
                self._add_face_processor(settings)
            else:
                logger.warning(f"Unknown processor: {processor_name}")
                
        self._initialized = True
        logger.info(f"VisionManager initialized with processors: {processor_order}")
    
    def _add_motion_processor(self, settings: Dict[str, Any]):
        """Add motion detection processor to pipeline."""
        motion_processor = MotionDetectionProcessor()
        motion_processor.initialize(settings.get("MotionDetector", {}))
        self._image_processor.add_processor(motion_processor)
        
    def _add_object_processor(self, settings: Dict[str, Any]):
        """Add object detection processor to pipeline.""" 
        from .pipeline.processors.ObjectDetectionProcessor import ObjectDetectionProcessor
        object_processor = ObjectDetectionProcessor()
        object_processor.initialize(settings.get("ObjectDetector", {}))
        self._image_processor.add_processor(object_processor)
        
    def _add_face_processor(self, settings: Dict[str, Any]):
        """Add face recognition processor to pipeline (placeholder for future)."""
        # TODO: Implement FaceRecognitionProcessor when ready
        logger.info("Face recognition processor not yet implemented")
    
    def update(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Process frame through the pipeline and return detection results.
        
        Args:
            frame: Input image frame
            
        Returns:
            Dictionary with detection results
        """
        if not self._initialized:
            raise RuntimeError("VisionManager not initialized. Call initialize() first.")
            
        start_time = time.time()
        
        # Process through pipeline
        initial_metadata = {'timestamp': time.time()}
        processed_frame, metadata = self._image_processor.process(frame, initial_metadata)
        
        processing_time = time.time() - start_time
        
        # Extract results from metadata
        results = {
            'motion_detected': metadata.get('motion_detected', False),
            'objects_detected': metadata.get('detected_objects', []),
            'faces_detected': metadata.get('detected_faces', []),
            'processing_time': processing_time,
            'metadata': metadata,
            'processed_frame': processed_frame
        }
        
        self._last_results = results
        return results
    
    def draw(self, frame: np.ndarray) -> np.ndarray:
        """
        Get frame with all detection results drawn.
        
        Args:
            frame: Original frame
            
        Returns:
            Frame with all detections drawn (from pipeline processing)
        """
        if not self._initialized:
            return frame
            
        # Pipeline processors handle drawing, return processed frame
        return self._last_results.get('processed_frame', frame)
    
    def get_last_results(self) -> Dict[str, Any]:
        """Get the last detection results."""
        return self._last_results.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics from the pipeline."""
        if self._image_processor:
            return self._image_processor.get_statistics()
        else:
            return {'total_processed': 0, 'processors': []}
    
    def get_processor_by_name(self, name: str):
        """Get a specific processor from the pipeline."""
        if self._image_processor:
            for processor in self._image_processor._processors:
                if processor.name == name:
                    return processor
        return None
    
    def enable_processor(self, name: str, enabled: bool = True):
        """Enable or disable a specific processor."""
        processor = self.get_processor_by_name(name)
        if processor:
            processor.enabled = enabled
            logger.info(f"Processor {name} {'enabled' if enabled else 'disabled'}")
        else:
            logger.warning(f"Processor {name} not found")


def main():
    """Test function for VisionManager."""
    print("Testing VisionManager (Pipeline Mode)...")
    
    # Test settings - simplified for pipeline-only approach
    test_settings = {
        "Vision": {
            "enabled_processors": ["motion", "object"],
            "processor_order": ["motion", "object"],
            "performance_monitoring": True
        },
        "MotionDetector": {
            "enabled": True,
            "history": 50,
            "motion_threshold": 200,
            "draw_results": True
        },
        "ObjectDetector": {
            "enabled": True,
            "weights_path": "yolov3.weights",
            "config_path": "yolov3.cfg", 
            "classes_path": "coco.names",
            "confidence_threshold": 0.5,
            "nms_threshold": 0.4,
            "draw_results": True
        }
    }
    
    # Test image path
    test_image_path = "test_image.jpg"
    
    try:
        # Create and initialize VisionManager
        vision_manager = VisionManager()
        vision_manager.initialize(test_settings)
        
        # Load test image
        if cv2 is not None:
            frame = cv2.imread(test_image_path)
            if frame is not None:
                print(f"Processing test image: {test_image_path}")
                
                # Run detection
                results = vision_manager.update(frame)
                
                print(f"Processing time: {results['processing_time']:.3f}s")
                print(f"Motion detected: {results['motion_detected']}")
                print(f"Objects detected: {len(results['objects_detected'])}")
                
                for obj in results['objects_detected']:
                    print(f"  - {obj.class_name}: {obj.confidence:.2f}")
                
                # Draw results
                result_frame = vision_manager.draw(frame)
                cv2.imwrite("vision_manager_result.jpg", result_frame)
                print("Result saved to vision_manager_result.jpg")
                
            else:
                print(f"Could not load test image: {test_image_path}")
        else:
            print("OpenCV not available for testing")
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()