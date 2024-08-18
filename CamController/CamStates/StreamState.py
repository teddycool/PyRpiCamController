import os
import time
from Connectivity import WiFi
from CamStates import BaseState
from StreamingServer import Pi2StreamingServer


class StreamState(BaseState.BaseState):
    def __init__(self):
        super(StreamState, self).__init__()     
        return


    def initialize(self, context):
        #Init clockinit state
        print ("StreamState initialize..")        
         #Set up cam as defined in the settings
        self.picam2streamer.initialize(context)
        return

    def update(self, context):
        # Camera runs in the background
        return
    
    def __del__(self):
        print ("Delete...")
        

if __name__ == "__main__":
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (800, 600)}))
    #create_video_configuration(controls={"FrameDurationLimits": (40000, 40000)})
    output = StreamingOutput()
    picam2.start_recording(JpegEncoder(), FileOutput(output))

    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        picam2.stop_recording()