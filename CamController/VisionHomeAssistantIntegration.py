# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

"""
Example integration showing how to combine VisionManager with HomeAssistantMQTT
for both Cam and Stream modes.
"""

import time
import logging
from typing import Dict, Any
import cv2

# Import vision and connectivity components
from Vision.VisionManager import VisionManager
from Connectivity.HomeAssistantMQTT import HomeAssistantMQTT

logger = logging.getLogger("cam.integration.vision_ha")


class VisionHomeAssistantIntegration:
    """
    Integration class that combines vision processing with Home Assistant MQTT reporting.
    
    Works for both Cam (capture photos) and Stream (continuous video) modes.
    """
    
    def __init__(self):
        self.vision_manager = None
        self.ha_mqtt = None
        self._last_heartbeat = 0
        self._heartbeat_interval = 300  # 5 minutes default
        self._initialized = False
        
    def initialize(self, settings: Dict[str, Any]) -> bool:
        """
        Initialize both vision processing and MQTT connectivity.
        
        Args:
            settings: Complete settings dictionary containing Vision and HomeAssistantMQTT sections
            
        Returns:
            True if initialization successful
        """
        try:
            # Initialize Vision Manager
            self.vision_manager = VisionManager()
            if not self.vision_manager:
                logger.error("Failed to create VisionManager")
                return False
                
            self.vision_manager.initialize(settings)
            logger.info("VisionManager initialized successfully")
            
            # Initialize Home Assistant MQTT
            self.ha_mqtt = HomeAssistantMQTT()
            mqtt_success = self.ha_mqtt.initialize(settings)
            
            if mqtt_success:
                logger.info("HomeAssistantMQTT initialized successfully") 
            else:
                logger.warning("HomeAssistantMQTT initialization failed, continuing without MQTT")
            
            # Get heartbeat interval
            ha_settings = settings.get("HomeAssistantMQTT", {})
            self._heartbeat_interval = ha_settings.get("heartbeat_interval", 300)
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize VisionHomeAssistantIntegration: {e}")
            return False
    
    def process_frame(self, frame) -> Dict[str, Any]:
        """
        Process a single frame through vision pipeline and send results to Home Assistant.
        
        Args:
            frame: OpenCV image frame (BGR format)
            
        Returns:
            Vision processing results
        """
        if not self._initialized:
            logger.warning("Integration not initialized")
            return {}
            
        try:
            # Process frame through vision pipeline
            vision_results = self.vision_manager.update(frame)
            
            # Send results to Home Assistant if MQTT is connected
            if self.ha_mqtt and self.ha_mqtt.is_connected():
                self.ha_mqtt.send_vision_results(vision_results)
            
            # Send periodic heartbeat
            self._send_heartbeat_if_needed()
            
            return vision_results
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {}
    
    def process_image_file(self, image_path: str) -> Dict[str, Any]:
        """
        Process a single image file (for Cam mode).
        
        Args:
            image_path: Path to image file
            
        Returns:
            Vision processing results
        """
        try:
            # Load image
            frame = cv2.imread(image_path)
            if frame is None:
                logger.error(f"Could not load image from {image_path}")
                return {}
            
            # Process the frame
            return self.process_frame(frame)
            
        except Exception as e:
            logger.error(f"Error processing image file {image_path}: {e}")
            return {}
    
    def get_annotated_frame(self, frame):
        """
        Get frame with vision annotations drawn.
        
        Args:
            frame: Original frame
            
        Returns:
            Frame with annotations
        """
        if self.vision_manager:
            return self.vision_manager.draw(frame)
        return frame
    
    def _send_heartbeat_if_needed(self):
        """Send heartbeat if interval has elapsed."""
        current_time = time.time()
        if current_time - self._last_heartbeat > self._heartbeat_interval:
            if self.ha_mqtt and self.ha_mqtt.is_connected():
                self.ha_mqtt.send_heartbeat()
            self._last_heartbeat = current_time
    
    def get_vision_statistics(self) -> Dict[str, Any]:
        """Get vision processing statistics."""
        if self.vision_manager:
            return self.vision_manager.get_statistics()
        return {}
    
    def enable_vision_processor(self, processor_name: str, enabled: bool = True):
        """Enable or disable a specific vision processor."""
        if self.vision_manager:
            self.vision_manager.enable_processor(processor_name, enabled)
    
    def is_mqtt_connected(self) -> bool:
        """Check if MQTT connection is active."""
        return self.ha_mqtt and self.ha_mqtt.is_connected()
    
    def shutdown(self):
        """Clean shutdown of all components."""
        logger.info("Shutting down VisionHomeAssistantIntegration")
        
        if self.ha_mqtt:
            self.ha_mqtt.disconnect()
            
        self._initialized = False


# Example usage functions for different modes

def example_cam_mode():
    """Example usage for Cam mode (single image processing)."""
    print("\\n=== CAM MODE EXAMPLE ===")
    
    # Example settings
    settings = {
        "Vision": {
            "enabled_processors": ["motion", "object"],
            "processor_order": ["motion", "object"]
        },
        "MotionDetector": {
            "enabled": True,
            "history": 50,
            "motion_threshold": 200
        },
        "ObjectDetector": {
            "enabled": True,
            "weights_path": "models/yolov3.weights",
            "config_path": "models/yolov3.cfg",
            "confidence_threshold": 0.5
        },
        "HomeAssistantMQTT": {
            "enabled": True,
            "broker_host": "homeassistant.local",
            "device_name": "Garden Camera",
            "send_discovery": True
        }
    }
    
    # Initialize integration
    integration = VisionHomeAssistantIntegration()
    
    if integration.initialize(settings):
        # Process a captured image
        image_path = "captured_image.jpg"
        results = integration.process_image_file(image_path)
        
        if results:
            print(f"Motion detected: {results.get('motion_detected')}")
            print(f"Objects found: {len(results.get('objects_detected', []))}")
            print(f"Processing time: {results.get('processing_time'):.3f}s")
        
        integration.shutdown()


def example_stream_mode():
    """Example usage for Stream mode (continuous video processing)."""
    print("\\n=== STREAM MODE EXAMPLE ===")
    
    # Example settings (same as cam mode)
    settings = {
        "Vision": {
            "enabled_processors": ["motion", "object"],
            "processor_order": ["motion", "object"]
        },
        "MotionDetector": {
            "enabled": True,
            "history": 50,
            "motion_threshold": 200
        },
        "ObjectDetector": {
            "enabled": True,
            "weights_path": "models/yolov3.weights", 
            "config_path": "models/yolov3.cfg",
            "confidence_threshold": 0.5
        },
        "HomeAssistantMQTT": {
            "enabled": True,
            "broker_host": "homeassistant.local",
            "device_name": "Security Camera",
            "report_all_frames": False  # Only report on changes
        }
    }
    
    # Initialize integration
    integration = VisionHomeAssistantIntegration()
    
    if integration.initialize(settings):
        # Simulate video stream processing
        print("Processing video stream... (press Ctrl+C to stop)")
        
        # Example: process frames from camera or video file
        # cap = cv2.VideoCapture(0)  # For webcam
        # cap = cv2.VideoCapture("video.mp4")  # For video file
        
        try:
            frame_count = 0
            while frame_count < 10:  # Limit for example
                # frame_ret, frame = cap.read()
                # if not frame_ret:
                #     break
                
                # For demo, create a dummy frame
                frame = None  # Replace with actual frame
                
                if frame is not None:
                    results = integration.process_frame(frame)
                    
                    if frame_count % 30 == 0:  # Log every 30 frames
                        print(f"Frame {frame_count}: Motion={results.get('motion_detected')}, "
                              f"Objects={len(results.get('objects_detected', []))}")
                
                frame_count += 1
                time.sleep(0.1)  # Simulate frame rate
                
        except KeyboardInterrupt:
            print("\\nStopping stream processing...")
        
        # cap.release()
        integration.shutdown()


def main():
    """Test and demonstration function."""
    print("VisionHomeAssistantIntegration Examples")
    print("=======================================")
    
    try:
        # Run examples
        example_cam_mode()
        example_stream_mode()
        
        print("\\n=== JSON MESSAGE EXAMPLES ===")
        
        # Show example JSON structures
        motion_example = {
            "timestamp": "2026-01-19T10:30:45.123Z",
            "detected": True,
            "processing_time": 0.045
        }
        
        objects_example = {
            "timestamp": "2026-01-19T10:30:45.123Z", 
            "objects": [
                {
                    "class": "person",
                    "confidence": 0.92,
                    "bbox": {"x": 100, "y": 150, "width": 80, "height": 200}
                },
                {
                    "class": "car", 
                    "confidence": 0.87,
                    "bbox": {"x": 300, "y": 200, "width": 150, "height": 100}
                }
            ],
            "processing_time": 0.045
        }
        
        summary_example = {
            "timestamp": "2026-01-19T10:30:45.123Z",
            "motion_detected": True,
            "total_objects": 2,
            "persons": 1, 
            "vehicles": 1,
            "animals": 0,
            "object_counts": {"person": 1, "car": 1},
            "processing_time": 0.045
        }
        
        import json
        print("\\nMotion Message:")
        print(json.dumps(motion_example, indent=2))
        
        print("\\nObjects Message:")
        print(json.dumps(objects_example, indent=2))
        
        print("\\nSummary Message:")
        print(json.dumps(summary_example, indent=2))
        
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()