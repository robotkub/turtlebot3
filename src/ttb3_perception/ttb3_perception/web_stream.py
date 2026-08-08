#!/usr/bin/env python3
"""Serves the camera as a plain web page -- no Foxglove, no laptop stack.

    http://skuba.local:8080/

Why this exists next to `./ttb3 snap` and `visualize:=true`: both of those
need the laptop-side Docker stack (or Foxglove Studio) up and pointed at the
robot. Sometimes you just want to check the lens isn't covered from a phone
on the same WiFi, without any of that -- this runs entirely on the Pi and
needs nothing but a browser.

Subscribes to /image_raw by default -- the uncompressed feed straight off
usb_cam's decode, before image_transport's JPEG compressor touches it. That
makes this the thing to point at when you want to know what the sensor is
actually producing, not what survived a second JPEG pass (`/image_raw` is
also what `apriltag_node` and `victim_detector` read, so this shows exactly
their input). Point `topic` at `/image_raw/compressed` instead if you'd
rather re-serve the already-compressed bytes with no extra decode/encode
work on the Pi -- topic name picks the message type the same way
`./ttb3 snap` does: a `/compressed` suffix means CompressedImage, anything
else means Image.

Raw frames get JPEG-encoded here (cv2.imencode) since a browser can't render
raw RGB/BGR bytes; compressed frames are re-served as-is.

http.server, not Flask/aiohttp: nothing beyond the stdlib (plus opencv,
already installed for perception) is needed here, and a camera preview does
not need more than ThreadingHTTPServer gives it.
"""
import threading
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE_TEMPLATE = """<!doctype html>
<html><head><title>ttb3 camera</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ background:#111; margin:0; display:flex; flex-direction:column;
         align-items:center; font-family:sans-serif; color:#ddd; }}
  h1 {{ font-size:1rem; font-weight:normal; margin:0.75rem; }}
  img {{ max-width:100%; height:auto; }}
</style></head>
<body>
<h1>ttb3 camera -- {topic}</h1>
<img src="/stream">
</body></html>
"""

_BOUNDARY = 'ttb3frame'


class _latest_frame:
    """Shared mailbox between the ROS callback thread and HTTP handler
    threads -- one lock, one slot, always the newest frame."""

    def __init__(self):
        self._lock = threading.Lock()
        self._jpeg = None

    def put(self, jpeg_bytes):
        with self._lock:
            self._jpeg = jpeg_bytes

    def get(self):
        with self._lock:
            return self._jpeg


class WebStreamNode(Node):

    def __init__(self, frame_box: _latest_frame):
        super().__init__('web_stream')
        self.declare_parameter('topic', '/image_raw')
        self.declare_parameter('port', 8080)
        topic = self.get_parameter('topic').value
        self._frame_box = frame_box
        if topic.endswith('/compressed'):
            self.create_subscription(
                CompressedImage, topic, self._on_compressed, 10)
        else:
            self.create_subscription(Image, topic, self._on_raw, 10)
        self.get_logger().info(f'serving {topic} at http://0.0.0.0:'
                                f'{self.get_parameter("port").value}/')

    def _on_compressed(self, msg: CompressedImage):
        self._frame_box.put(bytes(msg.data))

    def _on_raw(self, msg: Image):
        frame = np.frombuffer(bytes(msg.data), np.uint8).reshape(
            msg.height, msg.width, -1)
        if msg.encoding == 'rgb8':
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ok, jpeg = cv2.imencode('.jpg', frame)
        if ok:
            self._frame_box.put(jpeg.tobytes())


def _make_handler(frame_box: _latest_frame, topic, logger):
    page = PAGE_TEMPLATE.format(topic=topic).encode()

    class Handler(BaseHTTPRequestHandler):

        def log_message(self, fmt, *args):
            pass  # BaseHTTPRequestHandler logs to stderr per request; noisy

        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', str(len(page)))
                self.end_headers()
                self.wfile.write(page)
            elif self.path == '/snapshot.jpg':
                jpeg = frame_box.get()
                if jpeg is None:
                    self.send_response(503)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(jpeg)))
                self.end_headers()
                self.wfile.write(jpeg)
            elif self.path == '/stream':
                self._stream_mjpeg()
            else:
                self.send_response(404)
                self.end_headers()

        def _stream_mjpeg(self):
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header(
                'Content-Type',
                f'multipart/x-mixed-replace; boundary={_BOUNDARY}')
            self.end_headers()
            last_sent = None
            try:
                while True:
                    jpeg = frame_box.get()
                    # Don't resend a frame the camera hasn't refreshed yet --
                    # at 4fps that would just be wasted bandwidth to the
                    # browser, not a smoother picture.
                    if jpeg is not None and jpeg is not last_sent:
                        last_sent = jpeg
                        self.wfile.write(f'--{_BOUNDARY}\r\n'.encode())
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(
                            f'Content-Length: {len(jpeg)}\r\n\r\n'.encode())
                        self.wfile.write(jpeg)
                        self.wfile.write(b'\r\n')
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError):
                pass  # browser navigated away or closed the tab

    return Handler


def main():
    rclpy.init()
    frame_box = _latest_frame()
    node = WebStreamNode(frame_box)

    port = node.get_parameter('port').value
    topic = node.get_parameter('topic').value
    httpd = ThreadingHTTPServer(
        ('0.0.0.0', port), _make_handler(frame_box, topic, node.get_logger()))
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
