# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

"""
Modern Streaming Server for PyRpiCamController

Features:
- Support for Picamera2 (Pi Camera modules)
- Fallback to OpenCV for USB webcams
- Integrated with unified settings system
- Thread-safe operation
- Proper resource cleanup
- Configurable from web GUI
- MJPEG streaming with modern web interface
"""

import io
import logging
import socketserver
from http import server
from threading import Condition, Thread
import time
import socket
from typing import Optional, Dict, Any
import json

# Add project root to path for settings manager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Settings.settings_manager import settings_manager

logger = logging.getLogger("cam.streaming")

try:
    from picamera2 import Picamera2
    from picamera2.encoders import JpegEncoder, MJPEGEncoder
    from picamera2.outputs import FileOutput
    PICAMERA2_AVAILABLE = True
    logger.info("Picamera2 available")
except ImportError:
    PICAMERA2_AVAILABLE = False
    logger.warning("Picamera2 not available, will use OpenCV fallback")

try:
    import cv2
    OPENCV_AVAILABLE = True
    logger.info("OpenCV available")
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available")


class StreamingOutput(io.BufferedIOBase):
    """Thread-safe frame buffer for MJPEG streaming"""
    
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        self.clients = 0
        
        # FPS tracking
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps_history = []
        self.current_fps = 0.0
        self.last_frame_time = 0.0
    
    def write(self, buf):
        current_time = time.time()
        
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
            
            # Update FPS tracking
            self.frame_count += 1
            
            # Calculate instantaneous frame interval
            if self.last_frame_time > 0:
                frame_interval = current_time - self.last_frame_time
                if frame_interval > 0:
                    instantaneous_fps = 1.0 / frame_interval
                    self.fps_history.append(instantaneous_fps)
                    
                    # Keep only last 30 frames for rolling average
                    if len(self.fps_history) > 30:
                        self.fps_history.pop(0)
            
            self.last_frame_time = current_time
            
            # Update average FPS every second
            if current_time - self.last_fps_time >= 1.0:
                if self.fps_history:
                    self.current_fps = sum(self.fps_history) / len(self.fps_history)
                self.last_fps_time = current_time
                
        return len(buf)
    
    def get_frame(self, timeout=5.0):
        """Get the latest frame with timeout"""
        with self.condition:
            if self.condition.wait(timeout):
                return self.frame
        return None
    
    def get_fps(self):
        """Get current actual FPS"""
        return round(self.current_fps, 1)


class StreamingHandler(server.BaseHTTPRequestHandler):
    """HTTP request handler for streaming server"""
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging to avoid spam"""
        logger.debug(f"HTTP: {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == '/':
                self._serve_index()
            elif self.path == '/index.html':
                self._serve_index()
            elif self.path == '/stream.mjpg':
                self._serve_stream()
            elif self.path == '/api/info':
                self._serve_api_info()
            elif self.path == '/api/settings':
                self._serve_api_settings()
            else:
                self.send_error(404)
        except Exception as e:
            logger.error(f"Error handling request {self.path}: {e}")
            self.send_error(500)
    
    def _serve_index(self):
        """Serve the main streaming page"""
        try:
            # Get settings for page customization
            title = settings_manager.get('Stream.pagetitle', 'Camera Stream')
            headline = settings_manager.get('Stream.h1title', 'Live Camera Stream')
            resolution = settings_manager.get('Stream.resolution', [800, 600])
            width, height = resolution[0], resolution[1]
            
            # Get network info
            hostname = socket.gethostname()
            port = settings_manager.get('Stream.port', 8000)
            
            # Generate modern HTML page
            page_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            color: white;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            text-align: center;
        }}
        h1 {{
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .stream-container {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .stream-image {{
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .info-panel {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        .info-card {{
            background: rgba(255,255,255,0.1);
            padding: 15px 25px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #4CAF50;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
        .footer {{
            margin-top: 30px;
            opacity: 0.7;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1><span class="status-indicator"></span>{headline}</h1>
        
        <div class="stream-container">
            <img src="/stream.mjpg" 
                 class="stream-image"
                 alt="Live Camera Stream" 
                 onerror="this.style.display='none'; document.getElementById('error-msg').style.display='block';">
            <div id="error-msg" style="display: none; color: #ff6b6b; padding: 20px;">
                <h3>Stream Unavailable</h3>
                <p>Camera stream is not available. Check camera connection and settings.</p>
            </div>
        </div>
        
        <div class="info-panel">
            <div class="info-card">
                <strong>Resolution</strong><br>
                {width} × {height}
            </div>
            <div class="info-card">
                <strong>Target FPS</strong><br>
                <span id="targetFps">{settings_manager.get('Stream.framerate', 15)}</span>
            </div>
            <div class="info-card">
                <strong>Actual FPS</strong><br>
                <span id="actualFps" style="font-weight: bold; color: #007bff;">--</span>
            </div>
            <div class="info-card">
                <strong>Server</strong><br>
                {hostname}:{port}
            </div>
        </div>
        
        <div class="footer">
            <p>PyRpiCamController Streaming Server</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh stream on error
        document.querySelector('.stream-image').addEventListener('error', function() {{
            setTimeout(() => {{
                this.src = '/stream.mjpg?' + Date.now();
            }}, 5000);
        }});
        
        // Update info periodically
        setInterval(() => {{
            fetch('/api/info')
                .then(response => response.json())
                .then(data => {{
                    const actualFpsElement = document.getElementById('actualFps');
                    if (actualFpsElement && data.actual_fps !== undefined) {{
                        const actualFps = data.actual_fps;
                        const targetFps = parseInt(document.getElementById('targetFps').textContent);
                        
                        actualFpsElement.textContent = actualFps.toFixed(1);
                        
                        // Color code based on performance
                        if (actualFps >= targetFps * 0.9) {{
                            actualFpsElement.style.color = '#28a745'; // Green
                        }} else if (actualFps >= targetFps * 0.7) {{
                            actualFpsElement.style.color = '#ffc107'; // Yellow
                        }} else {{
                            actualFpsElement.style.color = '#dc3545'; // Red
                        }}
                    }}
                }})
                .catch(err => console.log('Info update failed:', err));
        }}, 2000); // Update every 2 seconds
    </script>
</body>
</html>"""
            
            content = page_content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.send_header('Cache-Control', 'no-cache, private')
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            logger.error(f"Error serving index: {e}")
            self.send_error(500)
    
    def _serve_stream(self):
        """Serve MJPEG stream"""
        try:
            streaming_server = self.server.streaming_server
            output = streaming_server.output
            
            if not output:
                self.send_error(503, "Stream not available")
                return
            
            output.clients += 1
            logger.info(f"Client connected for streaming. Total clients: {output.clients}")
            
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            
            try:
                while True:
                    frame = output.get_frame(timeout=5.0)
                    if frame is None:
                        logger.warning("Frame timeout, client may disconnect")
                        break
                    
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                    
            except Exception as e:
                logger.info(f"Client disconnected: {e}")
            finally:
                output.clients -= 1
                logger.info(f"Client disconnected. Remaining clients: {output.clients}")
                
        except Exception as e:
            logger.error(f"Error serving stream: {e}")
            self.send_error(500)
    
    def _serve_api_info(self):
        """Serve streaming info API"""
        try:
            streaming_server = self.server.streaming_server
            actual_fps = 0.0
            
            if streaming_server and streaming_server.output:
                actual_fps = streaming_server.output.get_fps()
            
            info = {
                'status': 'running',
                'resolution': settings_manager.get('Stream.resolution', [800, 600]),
                'framerate': settings_manager.get('Stream.framerate', 15),
                'actual_fps': actual_fps,
                'port': settings_manager.get('Stream.port', 8000),
                'clients': getattr(streaming_server.output, 'clients', 0) if streaming_server and streaming_server.output else 0,
                'timestamp': time.time()
            }
            
            content = json.dumps(info).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            logger.error(f"Error serving API info: {e}")
            self.send_error(500)
    
    def _serve_api_settings(self):
        """Serve current stream settings"""
        try:
            stream_settings = {
                'resolution': settings_manager.get('Stream.resolution', [800, 600]),
                'framerate': settings_manager.get('Stream.framerate', 15),
                'port': settings_manager.get('Stream.port', 8000),
                'pagetitle': settings_manager.get('Stream.pagetitle', 'Camera Stream'),
                'h1title': settings_manager.get('Stream.h1title', 'Live Camera Stream')
            }
            
            content = json.dumps(stream_settings).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            logger.error(f"Error serving API settings: {e}")
            self.send_error(500)


class ModernStreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """Modern streaming server with camera support"""
    
    allow_reuse_address = True
    daemon_threads = True
    
    def __init__(self, server_address, handler_class, streaming_server):
        self.streaming_server = streaming_server
        super().__init__(server_address, handler_class)


class CameraStreamer:
    """Main camera streaming class"""
    
    def __init__(self):
        self.camera = None
        self.output = None
        self.server = None
        self.server_thread = None
        self.running = False
        self.camera_type = None
        
    def initialize(self, settings: Dict[str, Any]) -> bool:
        """Initialize camera and streaming server with settings"""
        try:
            logger.info("Initializing camera streamer...")
            
            # Get camera type from hardware config
            cam_chip = settings.get('CamChip', 'PiCam3')
            resolution = settings_manager.get('Stream.resolution', [800, 600])
            framerate = settings_manager.get('Stream.framerate', 15)
            port = settings_manager.get('Stream.port', 8000)
            
            logger.info(f"Camera type: {cam_chip}, Resolution: {resolution}, FPS: {framerate}, Port: {port}")
            
            # Initialize camera based on type
            if cam_chip in ['PiCam2', 'PiCam3', 'PiCamHQ'] and PICAMERA2_AVAILABLE:
                logger.info("Attempting Picamera2 initialization...")
                success = self._init_picamera2(resolution, framerate)
                self.camera_type = 'picamera2'
            elif cam_chip == 'WebCam' and OPENCV_AVAILABLE:
                logger.info("Attempting OpenCV initialization...")
                success = self._init_opencv(resolution, framerate)
                self.camera_type = 'opencv'
            else:
                logger.error(f"Unsupported camera type: {cam_chip}, Picamera2: {PICAMERA2_AVAILABLE}, OpenCV: {OPENCV_AVAILABLE}")
                return False
            
            if not success:
                logger.error("Camera initialization failed")
                return False
            
            # Start streaming server
            logger.info("Starting streaming server...")
            self._start_server(port)
            
            logger.info("Camera streamer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing camera streamer: {e}", exc_info=True)
            return False
    
    def _init_picamera2(self, resolution, framerate) -> bool:
        """Initialize Picamera2 for Pi camera modules"""
        try:
            logger.info("Initializing Picamera2...")
            
            # Check if camera is already in use
            try:
                self.camera = Picamera2()
                logger.info("Picamera2 instance created")
            except Exception as e:
                logger.error(f"Failed to create Picamera2 instance: {e}")
                return False
            
            # Configure camera for streaming
            try:
                video_config = self.camera.create_video_configuration(
                    main={"size": tuple(resolution), "format": "YUV420"},
                    controls={"FrameDurationLimits": (int(1000000/framerate), int(1000000/framerate))}
                )
                logger.info(f"Video config created: {video_config}")
                
                self.camera.configure(video_config)
                logger.info("Camera configured")
            except Exception as e:
                logger.error(f"Failed to configure camera: {e}")
                return False
            
            # Create output buffer
            self.output = StreamingOutput()
            logger.info("Output buffer created")
            
            # Start recording
            try:
                encoder = MJPEGEncoder(bitrate=10000000)
                self.camera.start_recording(encoder, FileOutput(self.output))
                logger.info("Recording started")
                
                # Mark as running
                self.running = True
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                return False
            
            logger.info("Picamera2 streaming started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Picamera2 initialization failed: {e}", exc_info=True)
            return False
    
    def _init_opencv(self, resolution, framerate) -> bool:
        """Initialize OpenCV for USB webcams"""
        try:
            logger.info("Initializing OpenCV webcam...")
            
            # Open camera
            self.camera = cv2.VideoCapture(0)
            
            if not self.camera.isOpened():
                logger.error("Failed to open webcam")
                return False
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, framerate)
            
            # Create output buffer
            self.output = StreamingOutput()
            
            # Start capture thread
            self._start_opencv_capture()
            
            logger.info("OpenCV webcam streaming started")
            return True
            
        except Exception as e:
            logger.error(f"OpenCV initialization failed: {e}")
            return False
    
    def _start_opencv_capture(self):
        """Start OpenCV frame capture in separate thread"""
        def capture_frames():
            while self.running:
                try:
                    ret, frame = self.camera.read()
                    if ret:
                        # Encode frame as JPEG
                        _, buffer = cv2.imencode('.jpg', frame)
                        self.output.write(buffer.tobytes())
                    else:
                        logger.warning("Failed to capture frame")
                        time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Frame capture error: {e}")
                    time.sleep(1)
        
        self.running = True
        self.capture_thread = Thread(target=capture_frames, daemon=True)
        self.capture_thread.start()
    
    def _start_server(self, port):
        """Start HTTP streaming server"""
        try:
            logger.info(f"Starting streaming server on port {port}...")
            
            address = ('', port)
            self.server = ModernStreamingServer(address, StreamingHandler, self)
            
            # Start server in separate thread
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            hostname = socket.gethostname()
            logger.info(f"Streaming server running on http://{hostname}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to start streaming server: {e}")
            raise
    
    def stop(self):
        """Stop streaming and cleanup resources"""
        try:
            logger.info("Stopping camera streamer...")
            
            self.running = False
            
            # Stop server
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            # Stop camera
            if self.camera_type == 'picamera2' and self.camera:
                self.camera.stop_recording()
                self.camera.close()
            elif self.camera_type == 'opencv' and self.camera:
                self.camera.release()
            
            logger.info("Camera streamer stopped")
            
        except Exception as e:
            logger.error(f"Error stopping camera streamer: {e}")
    
    def is_running(self) -> bool:
        """Check if streaming is active"""
        return self.running and self.server is not None


# Singleton instance for use by other modules
streaming_instance = None


def start_streaming(settings: Dict[str, Any]) -> bool:
    """Start streaming with given settings"""
    global streaming_instance
    
    if streaming_instance and streaming_instance.is_running():
        logger.warning("Streaming already running")
        return True
    
    streaming_instance = CameraStreamer()
    return streaming_instance.initialize(settings)


def stop_streaming():
    """Stop active streaming"""
    global streaming_instance
    
    if streaming_instance:
        streaming_instance.stop()
        streaming_instance = None


def is_streaming() -> bool:
    """Check if streaming is active"""
    return streaming_instance and streaming_instance.is_running()


if __name__ == "__main__":
    """Test streaming server standalone"""
    print("Testing Modern Streaming Server...")
    
    # Test with mock settings
    test_settings = {
        'CamChip': 'WebCam',  # Change to PiCam3 for Pi camera
    }
    
    streamer = CameraStreamer()
    
    if streamer.initialize(test_settings):
        print("Streaming server started successfully!")
        print(f"Open http://localhost:{settings_manager.get('Stream.port', 8000)} in your browser")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping streaming server...")
            streamer.stop()
            print("Streaming server stopped.")
    else:
        print("Failed to start streaming server!")