__author__ = 'teddycool'
# Web streaming
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

# https://randomnerdtutorials.com/video-streaming-with-raspberry-pi-camera/

#https://www.reddit.com/r/raspberry_pi/comments/5561tp/chromecastlike_connection_wifi_setup_for/

#sudo apt-get install python3-picamera 

import sys
sys.path.append('/home/pi/cam')
import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import time
import socket
import request

hostname = socket.gethostname()
ipaddress = socket.gethostbyname(hostname) #TODO: Fix, now only returns 127.0.0.1 :-(

from config import camconfig

res = str(camconfig["Video"]["width"]) + "x" + str(camconfig["Video"]["height"])
width = str(camconfig["Video"]["width"])
height = str(camconfig["Video"]["height"])
fr = camconfig["Video"]["framerate"]
pagetitle = camconfig["Server"]["pagetitle"]
pageheadline = camconfig["Server"]["pageheadline"]
serverport = camconfig["Server"]["port"]
camrottation = camconfig["Video"]["rotation"]

imagetransform = camconfig["Video"]["transform"]
itwidth = camconfig["Video"]["twidth"]
itheight = camconfig["Video"]["theight"]

PAGE="<html><head><title>" + pagetitle + "</title></head><body><center><h1>"

PAGE = PAGE +  pageheadline  + '</h1></center>'
PAGE = PAGE + '<center><img src="stream.mjpg" width="' + width +  '" height="' + height  +  '"></center>'
PAGE = PAGE + """\
</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
      #  elif self.path == '/calibration':
      #      self.request.
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True



with picamera.PiCamera(resolution=res, framerate=fr) as camera:

   #It is really important to fix the values to make the calibration and detection work!
    print("Warning up, plase wait....")
    camera.iso = 100
    # Wait for the automatic gain control to settle
    time.sleep(5)
    # Now fix the values
    camera.shutter_speed = camera.exposure_speed
    camera.exposure_mode = 'off'
    g = camera.awb_gains
    camera.awb_mode = 'off'
    camera.awb_gains = g

    print("Preparing the image stream....")
    output = StreamingOutput()
    camera.rotation = camrottation
    print("Starting the image stream....")
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', serverport)
        print("Server running on " + hostname + " " + ipaddress + ":" + str(serverport))
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()