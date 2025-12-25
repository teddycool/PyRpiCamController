# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

import time
from CamStates import BaseState
from StreamingServer import ModernStreamingServer
import logging

logger = logging.getLogger("cam.state.streamstate")


class StreamState(BaseState.BaseState):
    def __init__(self):
        super(StreamState, self).__init__()
        self._streaming_server = None
        return

    def initialize(self, settings):
        """Initialize streaming state with camera and server"""
        logger.info("StreamState initialize...")
        
        try:
            logger.info(f"Starting streaming with settings: CamChip={settings.get('CamChip', 'Unknown')}")
            
            # Start streaming with the modern streaming server
            success = ModernStreamingServer.start_streaming(settings)
            
            if success:
                logger.info("Streaming server started successfully")
                self._streaming_server = ModernStreamingServer.streaming_instance
            else:
                logger.error("Failed to start streaming server")
                raise Exception("Streaming server initialization failed")
                
        except Exception as e:
            logger.error(f"StreamState initialization failed: {e}", exc_info=True)
            raise
        
        return

    def update(self, context):
        """Update streaming state - camera runs in background"""
        # Check if streaming is still active
        if not ModernStreamingServer.is_streaming():
            logger.warning("Streaming stopped unexpectedly")
            # Could trigger state change back to PostState here
        return
    
    def cleanup(self):
        """Clean up streaming resources for settings reload"""
        logger.info("StreamState cleanup for settings reload...")
        try:
            # Don't fully stop streaming, just prepare for re-initialization
            if self._streaming_server:
                # Store current streaming state
                was_running = ModernStreamingServer.is_streaming()
                if was_running:
                    logger.info("Temporarily pausing streaming for settings reload")
                    # We'll let the re-initialization handle the restart
        except Exception as e:
            logger.error(f"Error during StreamState cleanup: {e}")
    
    def stop_streaming(self):
        """Completely stop streaming (for state changes)"""
        logger.info("StreamState stop_streaming...")
        try:
            ModernStreamingServer.stop_streaming()
            self._streaming_server = None
            logger.info("Streaming server stopped completely")
        except Exception as e:
            logger.error(f"Error stopping streaming server: {e}")
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            self.stop_streaming()
        except:
            pass