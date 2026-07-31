#!/usr/bin/env python3
"""Finds the human-shaped 'victim' sign by HSV color threshold + contour finding
(SRS R4). Default color range targets red; retune config/victim_color.yaml once
the real sign is known. Handles the red hue wrap-around (0/180) via two ranges."""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

from ttb3_msgs.msg import VictimDetection


class VictimDetector(Node):

    def __init__(self):
        super().__init__('victim_detector')

        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('hsv_lower', [0, 120, 70])
        self.declare_parameter('hsv_upper', [10, 255, 255])
        self.declare_parameter('hsv_lower2', [170, 120, 70])
        self.declare_parameter('hsv_upper2', [180, 255, 255])
        self.declare_parameter('min_contour_area', 500)
        self.declare_parameter('publish_debug_image', False)

        image_topic = self.get_parameter('image_topic').value
        self._min_area = self.get_parameter('min_contour_area').value
        self._publish_debug = self.get_parameter('publish_debug_image').value

        self._bridge = CvBridge()
        self._pub = self.create_publisher(VictimDetection, '/victim_detections', 10)
        self._sub = self.create_subscription(Image, image_topic, self._on_image, 10)
        self._debug_pub = None
        if self._publish_debug:
            self._debug_pub = self.create_publisher(Image, '/victim_detector/debug_image', 1)

        self.get_logger().info(f'victim_detector: watching {image_topic} for the victim sign')

    def _color_mask(self, hsv):
        lower1 = np.array(self.get_parameter('hsv_lower').value, dtype=np.uint8)
        upper1 = np.array(self.get_parameter('hsv_upper').value, dtype=np.uint8)
        lower2 = np.array(self.get_parameter('hsv_lower2').value, dtype=np.uint8)
        upper2 = np.array(self.get_parameter('hsv_upper2').value, dtype=np.uint8)
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        return cv2.bitwise_or(mask1, mask2)

    def _on_image(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        height, width = frame.shape[:2]

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = self._color_mask(hsv)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = max(contours, key=cv2.contourArea) if contours else None

        out = VictimDetection()
        if best is not None and cv2.contourArea(best) >= self._min_area:
            x, y, w, h = cv2.boundingRect(best)
            cx, cy = x + w / 2.0, y + h / 2.0
            out.detected = True
            out.bearing = float((cx - width / 2.0) / (width / 2.0))
            out.apparent_size = float((w * h) / (width * height))
            out.image_x = float(cx)
            out.image_y = float(cy)
            if self._debug_pub is not None:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        else:
            out.detected = False

        self._pub.publish(out)

        if self._debug_pub is not None:
            debug_msg = self._bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            debug_msg.header = msg.header
            self._debug_pub.publish(debug_msg)


def main():
    rclpy.init()
    node = VictimDetector()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
