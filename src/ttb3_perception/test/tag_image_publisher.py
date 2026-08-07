#!/usr/bin/env python3
"""Publishes a still AprilTag PNG as a camera stream, for testing detection
without a printed tag and without the robot.

Why this exists: proving the perception pipeline works end to end otherwise
needs someone physically holding a tag in front of the camera. That makes the
one test you most want to run -- "can it read a tag at all?" -- impossible to
do remotely, and impossible to run in CI.

This publishes Image + CameraInfo on a topic pair that apriltag_node accepts,
so the REAL detector stack consumes it:

    python3 tag_image_publisher.py --tag 3
    ros2 launch ttb3_bringup detect.launch.py \\
        camera_image_topic:=/test_cam/image_raw remote_camera:=false

apriltag_node uses image_transport's CameraSubscriber, which derives the
camera_info topic from the image topic's parent namespace -- /test_cam/image_raw
means /test_cam/camera_info. Both are published here at the same rate, because
a missing camera_info is exactly the failure this is meant to detect: the node
then reports "Synchronized pairs: 0" and silently never looks at a frame.

The tag is composited onto a white 640x480 canvas rather than sent raw. A tag
that bleeds to the image edge has no quiet zone, and the detector needs white
margin around the black border to find the quad at all.
"""
import argparse
import os

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'data', 'apriltag')


class TagImagePublisher(Node):

    def __init__(self, tag_id, rate_hz, scale):
        super().__init__('tag_image_publisher')
        path = os.path.join(DATA_DIR, f'tag36h11_{tag_id}.png')
        tag = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if tag is None:
            raise SystemExit(f'cannot read {path}')

        self._frame = self._compose(tag, scale)
        self._bridge = CvBridge()
        h, w = self._frame.shape[:2]

        self._img_pub = self.create_publisher(Image, '/test_cam/image_raw', 10)
        self._info_pub = self.create_publisher(CameraInfo, '/test_cam/camera_info', 10)

        # A plausible pinhole intrinsic. Values only matter for pose estimation,
        # which tags_36h11.yaml disables (pose_estimation_method: "") -- but
        # camera_info must still ARRIVE or the subscriber never syncs.
        self._info = CameraInfo()
        self._info.width, self._info.height = w, h
        fx = fy = float(w)
        self._info.k = [fx, 0.0, w / 2.0, 0.0, fy, h / 2.0, 0.0, 0.0, 1.0]
        self._info.p = [fx, 0.0, w / 2.0, 0.0,
                        0.0, fy, h / 2.0, 0.0,
                        0.0, 0.0, 1.0, 0.0]
        self._info.distortion_model = 'plumb_bob'
        self._info.d = [0.0] * 5

        self.create_timer(1.0 / rate_hz, self._tick)
        self.get_logger().info(
            f'publishing tag36h11_{tag_id} as {w}x{h} @ {rate_hz}Hz on '
            f'/test_cam/image_raw (+ /test_cam/camera_info)')

    @staticmethod
    def _compose(tag, scale):
        """Centre the tag on a white 640x480 canvas, leaving a quiet zone."""
        canvas = np.full((480, 640), 255, dtype=np.uint8)
        side = max(1, int(min(canvas.shape) * scale))
        # INTER_NEAREST keeps the module edges hard; smooth interpolation blurs
        # the black/white boundaries the decoder thresholds on.
        tag = cv2.resize(tag, (side, side), interpolation=cv2.INTER_NEAREST)
        y = (canvas.shape[0] - side) // 2
        x = (canvas.shape[1] - side) // 2
        canvas[y:y + side, x:x + side] = tag
        return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)

    def _tick(self):
        stamp = self.get_clock().now().to_msg()
        msg = self._bridge.cv2_to_imgmsg(self._frame, encoding='bgr8')
        msg.header.stamp = stamp
        msg.header.frame_id = 'test_cam'
        self._info.header = msg.header
        self._img_pub.publish(msg)
        self._info_pub.publish(self._info)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', type=int, default=3, help='tag id (1, 2, 3 or 5)')
    ap.add_argument('--rate', type=float, default=4.0, help='publish rate (Hz)')
    ap.add_argument('--scale', type=float, default=0.5,
                    help='tag side as a fraction of image height')
    args, _ = ap.parse_known_args()

    rclpy.init()
    node = TagImagePublisher(args.tag, args.rate, args.scale)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
