# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None

logger = logging.getLogger("cam.connectivity.homeassistant")


class HomeAssistantMQTT:
    """
    MQTT client for sending vision pipeline results to Home Assistant.
    
    Handles connection management, message formatting, and automatic sensor 
    discovery for Home Assistant integration.
    """
    
    def __init__(self):
        self._client = None
        self._connected = False
        self._settings = {}
        self._device_id = "unknown"
        self._discovery_prefix = "homeassistant"
        self._last_motion_state = False
        self._last_objects = []
        
        if not MQTT_AVAILABLE:
            logger.error("paho-mqtt not available. Install with: pip install paho-mqtt")
    
    def initialize(self, settings: Dict[str, Any]):
        """
        Initialize MQTT client with settings.
        
        Expected settings:
        {
            "HomeAssistantMQTT": {
                "enabled": true,
                "broker_host": "homeassistant.local",
                "broker_port": 1883,
                "username": "mqtt_user",
                "password": "mqtt_password", 
                "device_name": "Camera_01",
                "discovery_prefix": "homeassistant",
                "qos": 0,
                "retain": true,
                "send_discovery": true,
                "motion_topic": "motion",
                "objects_topic": "objects",
                "summary_topic": "summary"
            }
        }
        """
        if not MQTT_AVAILABLE:
            logger.error("Cannot initialize HomeAssistantMQTT: paho-mqtt not installed")
            return False
            
        self._settings = settings.get("HomeAssistantMQTT", {})
        
        if not self._settings.get("enabled", False):
            logger.info("HomeAssistantMQTT disabled in settings")
            return False
        
        # Extract connection settings
        self._broker_host = self._settings.get("broker_host", "localhost")
        self._broker_port = self._settings.get("broker_port", 1883)
        self._username = self._settings.get("username")
        self._password = self._settings.get("password") 
        self._device_name = self._settings.get("device_name", "PyRpiCamController")
        self._device_id = self._device_name.lower().replace(" ", "_")
        self._discovery_prefix = self._settings.get("discovery_prefix", "homeassistant")
        
        # Message settings
        self._qos = self._settings.get("qos", 0)
        self._retain = self._settings.get("retain", True)
        self._send_discovery = self._settings.get("send_discovery", True)
        
        # Topic settings
        self._motion_topic = self._settings.get("motion_topic", "motion")
        self._objects_topic = self._settings.get("objects_topic", "objects") 
        self._summary_topic = self._settings.get("summary_topic", "summary")
        
        # Base topic for all messages
        self._base_topic = f"pyripicam/{self._device_id}"
        
        try:
            # Create MQTT client
            self._client = mqtt.Client(client_id=f"{self._device_id}_vision")
            
            # Set callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_publish = self._on_publish
            
            # Set credentials if provided
            if self._username and self._password:
                self._client.username_pw_set(self._username, self._password)
            
            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self._broker_host}:{self._broker_port}")
            self._client.connect(self._broker_host, self._broker_port, 60)
            self._client.loop_start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the MQTT broker.""" 
        if rc == 0:
            self._connected = True
            logger.info(f"Connected to MQTT broker with result code {rc}")
            
            if self._send_discovery:
                self._publish_discovery_configs()
        else:
            self._connected = False
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the MQTT broker."""
        self._connected = False
        logger.warning(f"Disconnected from MQTT broker with result code {rc}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for when a message is published."""
        logger.debug(f"Message {mid} published successfully")
    
    def _publish_discovery_configs(self):
        """Publish Home Assistant discovery configuration messages."""
        try:
            # Motion sensor discovery
            motion_config = {
                "name": f"{self._device_name} Motion",
                "state_topic": f"{self._base_topic}/{self._motion_topic}",
                "value_template": "{{ value_json.detected }}",
                "payload_on": True,
                "payload_off": False,
                "device_class": "motion",
                "unique_id": f"{self._device_id}_motion",
                "device": {
                    "identifiers": [self._device_id],
                    "name": self._device_name,
                    "model": "PyRpiCamController",
                    "manufacturer": "Custom"
                }
            }
            
            motion_discovery_topic = f"{self._discovery_prefix}/binary_sensor/{self._device_id}_motion/config"
            self._client.publish(motion_discovery_topic, json.dumps(motion_config), 
                               qos=self._qos, retain=True)
            
            # Object count sensor discovery
            objects_config = {
                "name": f"{self._device_name} Object Count", 
                "state_topic": f"{self._base_topic}/{self._summary_topic}",
                "value_template": "{{ value_json.total_objects }}",
                "unit_of_measurement": "objects",
                "unique_id": f"{self._device_id}_object_count",
                "device": {
                    "identifiers": [self._device_id],
                    "name": self._device_name,
                    "model": "PyRpiCamController", 
                    "manufacturer": "Custom"
                }
            }
            
            objects_discovery_topic = f"{self._discovery_prefix}/sensor/{self._device_id}_object_count/config"
            self._client.publish(objects_discovery_topic, json.dumps(objects_config),
                               qos=self._qos, retain=True)
            
            # Person count sensor discovery
            persons_config = {
                "name": f"{self._device_name} Person Count",
                "state_topic": f"{self._base_topic}/{self._summary_topic}",
                "value_template": "{{ value_json.persons }}",
                "unit_of_measurement": "persons", 
                "unique_id": f"{self._device_id}_person_count",
                "device": {
                    "identifiers": [self._device_id],
                    "name": self._device_name,
                    "model": "PyRpiCamController",
                    "manufacturer": "Custom"
                }
            }
            
            persons_discovery_topic = f"{self._discovery_prefix}/sensor/{self._device_id}_person_count/config"
            self._client.publish(persons_discovery_topic, json.dumps(persons_config),
                               qos=self._qos, retain=True)
            
            logger.info("Published Home Assistant discovery configurations")
            
        except Exception as e:
            logger.error(f"Error publishing discovery configs: {e}")
    
    def send_vision_results(self, vision_results: Dict[str, Any]):
        """
        Send vision pipeline results to Home Assistant via MQTT.
        
        Args:
            vision_results: Results from VisionManager.update()
        """
        if not self._connected or not MQTT_AVAILABLE:
            logger.debug("MQTT not connected, skipping vision results")
            return
        
        try:
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Extract results
            motion_detected = vision_results.get('motion_detected', False)
            detected_objects = vision_results.get('objects_detected', [])
            processing_time = vision_results.get('processing_time', 0.0)
            
            # Create motion message
            motion_message = {
                "timestamp": timestamp,
                "detected": motion_detected,
                "processing_time": processing_time
            }
            
            # Create objects message 
            objects_message = {
                "timestamp": timestamp,
                "objects": self._format_objects(detected_objects),
                "processing_time": processing_time
            }
            
            # Create summary message
            summary_message = self._create_summary(detected_objects, motion_detected, timestamp, processing_time)
            
            # Publish messages
            self._publish_message(f"{self._base_topic}/{self._motion_topic}", motion_message)
            self._publish_message(f"{self._base_topic}/{self._objects_topic}", objects_message)
            self._publish_message(f"{self._base_topic}/{self._summary_topic}", summary_message)
            
            # Store state for change detection
            self._last_motion_state = motion_detected
            self._last_objects = detected_objects
            
            logger.debug(f"Sent vision results: motion={motion_detected}, objects={len(detected_objects)}")
            
        except Exception as e:
            logger.error(f"Error sending vision results: {e}")
    
    def _format_objects(self, detected_objects: List) -> List[Dict[str, Any]]:
        """Format detected objects for MQTT message."""
        objects = []
        
        for obj in detected_objects:
            # Handle both DetectedObject instances and dictionaries
            if hasattr(obj, 'class_name'):
                # DetectedObject instance
                object_data = {
                    "class": obj.class_name,
                    "confidence": round(obj.confidence, 3),
                    "bbox": {
                        "x": obj.box[0],
                        "y": obj.box[1], 
                        "width": obj.box[2],
                        "height": obj.box[3]
                    }
                }
            else:
                # Dictionary format
                object_data = {
                    "class": obj.get('class_name', 'unknown'),
                    "confidence": round(obj.get('confidence', 0.0), 3),
                    "bbox": obj.get('box', {"x": 0, "y": 0, "width": 0, "height": 0})
                }
            
            objects.append(object_data)
        
        return objects
    
    def _create_summary(self, detected_objects: List, motion_detected: bool, 
                       timestamp: str, processing_time: float) -> Dict[str, Any]:
        """Create summary statistics for Home Assistant sensors."""
        
        # Count objects by type
        object_counts = {}
        for obj in detected_objects:
            class_name = obj.class_name if hasattr(obj, 'class_name') else obj.get('class_name', 'unknown')
            object_counts[class_name] = object_counts.get(class_name, 0) + 1
        
        # Special counts for common objects
        persons = object_counts.get('person', 0)
        vehicles = (object_counts.get('car', 0) + 
                   object_counts.get('truck', 0) + 
                   object_counts.get('bus', 0) + 
                   object_counts.get('motorbike', 0) + 
                   object_counts.get('bicycle', 0))
        animals = (object_counts.get('cat', 0) + 
                  object_counts.get('dog', 0) + 
                  object_counts.get('bird', 0) + 
                  object_counts.get('horse', 0))
        
        return {
            "timestamp": timestamp,
            "motion_detected": motion_detected,
            "total_objects": len(detected_objects),
            "persons": persons,
            "vehicles": vehicles,
            "animals": animals,
            "object_counts": object_counts,
            "processing_time": round(processing_time, 3)
        }
    
    def _publish_message(self, topic: str, message: Dict[str, Any]):
        """Publish a JSON message to MQTT topic."""
        try:
            json_message = json.dumps(message)
            result = self._client.publish(topic, json_message, qos=self._qos, retain=self._retain)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning(f"Failed to publish to {topic}: {result.rc}")
                
        except Exception as e:
            logger.error(f"Error publishing message to {topic}: {e}")
    
    def send_heartbeat(self):
        """Send heartbeat message to indicate the system is alive."""
        if not self._connected:
            return
            
        heartbeat = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "online",
            "device_id": self._device_id
        }
        
        self._publish_message(f"{self._base_topic}/heartbeat", heartbeat)
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self._client and self._connected:
            logger.info("Disconnecting from MQTT broker")
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self._connected and MQTT_AVAILABLE


def main():
    """Test function for HomeAssistantMQTT."""
    print("Testing HomeAssistantMQTT...")
    
    # Test settings
    test_settings = {
        "HomeAssistantMQTT": {
            "enabled": True,
            "broker_host": "localhost",  # Change to your broker
            "broker_port": 1883,
            "username": "mqtt_user",     # Optional
            "password": "mqtt_password", # Optional
            "device_name": "Test Camera",
            "discovery_prefix": "homeassistant",
            "qos": 0,
            "retain": True,
            "send_discovery": True
        }
    }
    
    # Mock vision results
    class MockDetectedObject:
        def __init__(self, class_name, confidence, box):
            self.class_name = class_name
            self.confidence = confidence
            self.box = box
    
    mock_vision_results = {
        'motion_detected': True,
        'objects_detected': [
            MockDetectedObject('person', 0.92, (100, 150, 80, 200)),
            MockDetectedObject('car', 0.87, (300, 200, 150, 100))
        ],
        'processing_time': 0.045
    }
    
    try:
        # Initialize MQTT client
        ha_mqtt = HomeAssistantMQTT()
        
        if ha_mqtt.initialize(test_settings):
            print("✓ MQTT client initialized successfully")
            
            # Wait for connection
            time.sleep(2)
            
            if ha_mqtt.is_connected():
                print("✓ Connected to MQTT broker")
                
                # Send test vision results
                ha_mqtt.send_vision_results(mock_vision_results)
                print("✓ Sent test vision results")
                
                # Send heartbeat
                ha_mqtt.send_heartbeat()
                print("✓ Sent heartbeat")
                
                # Wait a bit for messages to be sent
                time.sleep(1)
                
                print("\nTest completed! Check Home Assistant for new sensors:")
                print("- binary_sensor.test_camera_motion")
                print("- sensor.test_camera_object_count") 
                print("- sensor.test_camera_person_count")
                
            else:
                print("✗ Failed to connect to MQTT broker")
                
        else:
            print("✗ Failed to initialize MQTT client")
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            ha_mqtt.disconnect()
        except:
            pass


if __name__ == "__main__":
    main()