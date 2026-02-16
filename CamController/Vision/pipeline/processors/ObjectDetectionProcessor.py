# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import numpy as np
import cv2
import os
from typing import Dict, Any, Tuple, List
import logging
from ..ProcessorBase import ProcessorBase

logger = logging.getLogger("cam.vision.object")


class DetectedObject:
    """Represents a detected object with its properties."""
    def __init__(self, class_id: int, class_name: str, confidence: float, box: Tuple[int, int, int, int]):
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = confidence
        self.box = box  # (x, y, width, height)


class ObjectDetectionProcessor(ProcessorBase):
    """
    Object detection processor using YOLO framework.
    
    Wraps the standalone ObjectDetector to work within the pipeline system.
    Adds detected objects to metadata and optionally draws bounding boxes.
    """
    
    def __init__(self, name: str = "ObjectDetectionProcessor"):
        super().__init__(name)
        self._draw_results = True
        self._target_classes = None
        
        # YOLO detection components
        self._net = None
        self._output_layers = None
        self._classes = []
        self._colors = []
        self._detected_objects: List[DetectedObject] = []
        
        # Detection thresholds
        self._confidence_threshold = 0.5
        self._nms_threshold = 0.4
        
    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize object detection processor.
        
        Expected settings:
        - enabled: bool - whether object detection is enabled
        - draw_results: bool - whether to draw bounding boxes on image
        - target_classes: list - specific object classes to detect (None for all)
        - All ObjectDetector settings (weights_path, config_path, etc.)
        """
        super().initialize(settings)
        
        # Extract processor-specific settings
        self._draw_results = self.get_setting('draw_results', True)
        self._target_classes = self.get_setting('target_classes', None)
        
        # Get YOLO configuration
        weights_path = self.get_setting('weights_path', 'yolov3.weights')
        config_path = self.get_setting('config_path', 'yolov3.cfg')
        classes_path = self.get_setting('classes_path', 'coco.names')
        
        self._confidence_threshold = self.get_setting('confidence_threshold', 0.5)
        self._nms_threshold = self.get_setting('nms_threshold', 0.4)
        
        try:
            # Load YOLO network
            self._net = cv2.dnn.readNet(weights_path, config_path)
            
            # Get output layer names
            layer_names = self._net.getLayerNames()
            self._output_layers = [layer_names[i - 1] for i in self._net.getUnconnectedOutLayers()]
            
            # Load class names
            if os.path.exists(classes_path):
                with open(classes_path, 'r') as f:
                    self._classes = [line.strip() for line in f.readlines()]
            else:
                # Default COCO classes if file not found
                self._classes = self._get_default_coco_classes()
            
            # Generate random colors for each class
            self._colors = np.random.uniform(0, 255, size=(len(self._classes), 3))
            
            logger.info(f"ObjectDetectionProcessor initialized with {len(self._classes)} classes")
            
        except Exception as e:
            logger.error(f"Error initializing ObjectDetectionProcessor: {e}")
            # Initialize with empty values to prevent crashes
            self._net = None
            self._output_layers = []
            self._classes = []
            self._colors = []
    
    def process(self, image: np.ndarray, metadata: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process image for object detection.
        
        Args:
            image: Input image (BGR format)
            metadata: Current metadata dictionary
            
        Returns:
            Tuple of (processed_image, updated_metadata)
        """
        if not self.enabled or self._net is None:
            return image, metadata
            
        try:
            self._detected_objects = []
            height, width, channels = image.shape
            
            # Create blob from frame
            blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
            self._net.setInput(blob)
            
            # Run inference
            outputs = self._net.forward(self._output_layers)
            
            # Process detections
            boxes = []
            confidences = []
            class_ids = []
            
            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if confidence > self._confidence_threshold:
                        # Filter by target classes if specified
                        if self._target_classes is not None:
                            class_name = self._classes[class_id] if class_id < len(self._classes) else "Unknown"
                            if class_name not in self._target_classes:
                                continue
                                
                        # Object detected
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        # Rectangle coordinates
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
            
            # Apply Non-Maximum Suppression
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, self._confidence_threshold, self._nms_threshold)
            
            # Store detected objects
            if len(indexes) > 0:
                for i in indexes.flatten():
                    class_name = self._classes[class_ids[i]] if class_ids[i] < len(self._classes) else "Unknown"
                    detected_obj = DetectedObject(
                        class_ids[i], 
                        class_name, 
                        confidences[i], 
                        tuple(boxes[i])
                    )
                    self._detected_objects.append(detected_obj)
            
            # Filter by target classes if specified
            detected_objects = self._detected_objects
            if self._target_classes is not None:
                detected_objects = [obj for obj in detected_objects 
                                  if obj.class_name in self._target_classes]
            
            objects_detected = len(detected_objects) > 0
            
            # Update metadata
            metadata.update({
                'objects_detected': objects_detected,
                'detected_objects': detected_objects,
                'object_count': len(detected_objects),
                'object_classes': list(set(obj.class_name for obj in detected_objects))
            })
            
            # Add individual class counts
            class_counts = {}
            for obj in detected_objects:
                class_counts[obj.class_name] = class_counts.get(obj.class_name, 0) + 1
            metadata['object_class_counts'] = class_counts
            
            # Draw results if enabled
            processed_image = image
            if self._draw_results and detected_objects:
                processed_image = self._draw_detections(image.copy(), detected_objects)
                
            logger.debug(f"Detected {len(detected_objects)} objects: {metadata['object_classes']}")
            
            return processed_image, metadata
            
        except Exception as e:
            logger.error(f"Error in ObjectDetectionProcessor.process(): {e}")
            # Return original image and metadata on error
            metadata['object_detection_error'] = str(e)
            return image, metadata
    
    def _draw_detections(self, image: np.ndarray, detected_objects: List[DetectedObject]) -> np.ndarray:
        """Draw detection results on the image."""
        try:
            for obj in detected_objects:
                x, y, w, h = obj.box
                color = self._colors[obj.class_id % len(self._colors)]
                
                # Draw bounding box
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
                
                # Draw label with confidence
                label = f"{obj.class_name}: {obj.confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                # Draw label background
                cv2.rectangle(image, (x, y - label_size[1] - 10), (x + label_size[0], y), color, -1)
                
                # Draw label text
                cv2.putText(image, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        except Exception as e:
            logger.error(f"Error drawing detections: {e}")
            
        return image
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value with fallback to default."""
        return self._settings.get(key, default)
    
    def get_detected_objects(self) -> List[DetectedObject]:
        """Get the currently detected objects."""
        return self._detected_objects.copy()
    
    def has_object(self, class_name: str) -> bool:
        """Check if a specific object class was detected."""
        return any(obj.class_name == class_name for obj in self._detected_objects)
    
    def _get_default_coco_classes(self) -> List[str]:
        """Return default COCO class names if classes file is not available."""
        return [
            "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck",
            "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
            "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
            "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
            "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
            "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
            "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
            "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa",
            "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse",
            "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
            "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
            "toothbrush"
        ]


def main():
    """Test function for ObjectDetectionProcessor."""
    print("Testing ObjectDetectionProcessor...")
    
    # Test settings
    test_settings = {
        'enabled': True,
        'draw_results': True,
        'target_classes': None,  # Detect all classes
        'weights_path': 'yolov3.weights',
        'config_path': 'yolov3.cfg',
        'classes_path': 'coco.names',
        'confidence_threshold': 0.5,
        'nms_threshold': 0.4
    }
    
    # Test image path
    test_image_path = "test_image.jpg"
    
    try:
        # Create and initialize processor
        processor = ObjectDetectionProcessor()
        processor.initialize(test_settings)
        
        # Load test image
        import cv2
        import time
        
        if cv2 is not None:
            image = cv2.imread(test_image_path)
            if image is not None:
                print(f"Processing test image: {test_image_path}")
                
                # Initial metadata
                initial_metadata = {
                    'timestamp': time.time(),
                    'frame_id': 1
                }
                
                # Process image
                start_time = time.time()
                processed_image, metadata = processor.process(image, initial_metadata)
                processing_time = time.time() - start_time
                
                print(f"Processing time: {processing_time:.3f}s")
                print(f"Objects detected: {metadata.get('objects_detected', False)}")
                print(f"Object count: {metadata.get('object_count', 0)}")
                print(f"Object classes: {metadata.get('object_classes', [])}")
                print(f"Class counts: {metadata.get('object_class_counts', {})}")
                
                # Save result
                cv2.imwrite("object_processor_result.jpg", processed_image)
                print("Result saved to object_processor_result.jpg")
                
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