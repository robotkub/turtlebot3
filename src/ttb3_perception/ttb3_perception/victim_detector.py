#!/usr/bin/env python3
"""Finds the human-shaped 'victim' sign by HSV color threshold + contour finding
(SRS R4). Default color range targets the yellow sign; retune
config/victim_color.yaml on-site. The actual detection algorithm lives in
vision_core.detect_victim (ROS-free, so it's unit-tested in CI); this node is
just the ROS glue."""
import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

from ttb3_msgs.msg import VictimDetection

from .vision_core import detect_victim


class VictimDetector(Node):

    def __init__(self):
        super().__init__('victim_detector')

        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('hsv_lower', [20, 100, 100])
        self.declare_parameter('hsv_upper', [35, 255, 255])
        self.declare_parameter('hsv_lower2', [20, 100, 100])
        self.declare_parameter('hsv_upper2', [35, 255, 255])
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

    def _hsv_params(self):
        return dict(
            hsv_lower=self.get_parameter('hsv_lower').value,
            hsv_upper=self.get_parameter('hsv_upper').value,
            hsv_lower2=self.get_parameter('hsv_lower2').value,
            hsv_upper2=self.get_parameter('hsv_upper2').value,
            min_contour_area=self._min_area,
        )

    def _on_image(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        result = detect_victim(frame, annotate=self._publish_debug, **self._hsv_params())

        out = VictimDetection()
        out.detected = result['detected']
        if result['detected']:
            out.bearing = result['bearing']
            out.apparent_size = result['apparent_size']
            out.image_x = result['image_x']
            out.image_y = result['image_y']

        self._pub.publish(out)

        if self._debug_pub is not None:
            if result['detected'] and 'bbox' in result:
                x, y, w, h = result['bbox']
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
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
