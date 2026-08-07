#!/usr/bin/env python3
"""Saves camera frames to ./debug_images/ so you can actually LOOK at what the
detector is being fed.

Why this exists: when apriltag_detector says "no tag in view", that one line
covers two completely different failures -- the detector is broken, or the
picture is. Topic rates cannot tell them apart: a camera publishing the same
corrupt frame forever still reads 4 Hz on `ros2 topic hz`, and apriltag_node
still processes every one of them and honestly reports nothing. The only way
to separate the two is to open the image.

    ./ttb3 snap                     10 frames off the live camera
    ./ttb3 snap /test_cam/image_raw  ...off the synthetic tag publisher

Per frame it prints the numbers that identify a dead camera without opening
anything:

    00  11399 B  640x480  mean= 17.7  min=0 max=184  BGR= 0/30/0
    01  11399 B  640x480  mean= 17.7  min=0 max=184  BGR= 0/30/0  DUP

DUP means byte-identical to the previous frame. A live camera never repeats a
frame exactly -- sensor noise alone changes some pixel. All-DUP means the
driver is republishing one stale buffer, which is a USB/driver fault, not a
perception one. B or R stuck at exactly 0 means the MJPEG decode produced
garbage rather than a dark room.

Reads whichever message type the topic name implies -- a name ending in
/compressed is CompressedImage -- the same rule victim_detector.py uses, so
this can point at any camera topic in the graph without extra flags.
"""
import argparse
import os
import time
from datetime import datetime

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image


class FrameSaver(Node):

    def __init__(self, topic, count, out_dir):
        super().__init__('frame_saver')
        self._count = count
        self._out_dir = out_dir
        self._stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.saved = 0
        self.decode_failures = 0
        self.duplicates = 0
        self._prev_payload = None

        os.makedirs(out_dir, exist_ok=True)

        if topic.endswith('/compressed'):
            self._sub = self.create_subscription(
                CompressedImage, topic, self._on_compressed, 10)
        else:
            self._sub = self.create_subscription(Image, topic, self._on_raw, 10)

    def _on_compressed(self, msg: CompressedImage):
        payload = bytes(msg.data)
        # imdecode, not cv_bridge: a truncated or malformed JPEG must come back
        # as None to be COUNTED, and cv_bridge raises instead, which would kill
        # the callback on exactly the broken stream this exists to diagnose.
        frame = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
        self._record(frame, payload, len(payload))

    def _on_raw(self, msg: Image):
        payload = bytes(msg.data)
        frame = np.frombuffer(payload, np.uint8).reshape(
            msg.height, msg.width, -1)
        if msg.encoding == 'rgb8':
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        self._record(frame, payload, len(payload))

    def _record(self, frame, payload, nbytes):
        if self.saved >= self._count:
            return
        i = self.saved
        self.saved += 1

        if frame is None:
            self.decode_failures += 1
            print(f'  {i:02d}  {nbytes} B  DECODE FAILED (not a valid JPEG)')
            return

        dup = payload == self._prev_payload
        self._prev_payload = payload
        if dup:
            self.duplicates += 1

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]
        print(f'  {i:02d}  {nbytes} B  {w}x{h}  mean={gray.mean():5.1f}  '
              f'min={gray.min()} max={gray.max()}  '
              f'BGR={frame[:, :, 0].mean():.0f}/{frame[:, :, 1].mean():.0f}/'
              f'{frame[:, :, 2].mean():.0f}'
              f'{"  DUP" if dup else ""}')

        path = os.path.join(self._out_dir, f'{self._stamp}_{i:02d}.jpg')
        cv2.imwrite(path, frame)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default='/image_raw/compressed',
                    help='camera topic; a /compressed suffix selects '
                         'CompressedImage, anything else Image')
    ap.add_argument('--count', type=int, default=10, help='frames to save')
    ap.add_argument('--out', default='/debug_images',
                    help='output directory (mounted to ./debug_images on the host)')
    ap.add_argument('--timeout', type=float, default=20.0,
                    help='give up if the topic stays silent this long (s)')
    args, _ = ap.parse_known_args()

    rclpy.init()
    node = FrameSaver(args.topic, args.count, args.out)
    print(f'saving up to {args.count} frames from {args.topic} -> ./debug_images/')

    deadline = time.time() + args.timeout
    try:
        while rclpy.ok() and node.saved < args.count and time.time() < deadline:
            rclpy.spin_once(node, timeout_sec=0.5)
    except KeyboardInterrupt:
        pass

    if node.saved == 0:
        print(f'NOTHING RECEIVED on {args.topic} in {args.timeout:.0f}s -- is '
              f'the camera running? (`ros2 topic list`)')
    else:
        print(f'\nsaved {node.saved} frame(s) to ./debug_images/')
        if node.decode_failures:
            print(f'  {node.decode_failures} frame(s) failed to decode -- the '
                  f'JPEG stream itself is corrupt')
        # saved-1 because the first frame has nothing to compare against.
        if node.saved > 1 and node.duplicates == node.saved - 1:
            print('  EVERY frame was byte-identical: the camera is FROZEN, '
                  'republishing one stale buffer. Detection cannot work on '
                  'this -- fix the camera before suspecting the detector.')

    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == '__main__':
    main()
