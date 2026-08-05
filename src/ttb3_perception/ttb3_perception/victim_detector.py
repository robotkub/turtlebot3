#!/usr/bin/env python3
"""Finds the victim sign -- a HUMAN FIGURE -- with a MobileNet-SSD person
detector. NOT color-based: the sign is detected because it's a person,
regardless of what colour it wears. The detection algorithm lives in
vision_core.detect_person (ROS-free, so it's unit-tested in CI); this node is
just the ROS glue."""
import os

import cv2
import rclpy
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

from ttb3_msgs.msg import VictimDetection

from .vision_core import detect_person, load_person_net


class VictimDetector(Node):

    def __init__(self):
        super().__init__('victim_detector')

        share = get_package_share_directory('ttb3_perception')
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter(
            'prototxt', os.path.join(share, 'models', 'MobileNetSSD_deploy.prototxt'))
        self.declare_parameter(
            'caffemodel', os.path.join(share, 'models', 'MobileNetSSD_deploy.caffemodel'))
        self.declare_parameter('confidence_threshold', 0.45)
        self.declare_parameter('publish_debug_image', False)

        image_topic = self.get_parameter('image_topic').value
        self._conf = self.get_parameter('confidence_threshold').value
        self._publish_debug = self.get_parameter('publish_debug_image').value

        self._net = load_person_net(
            self.get_parameter('prototxt').value,
            self.get_parameter('caffemodel').value)

        self._bridge = CvBridge()
        self._pub = self.create_publisher(VictimDetection, '/victim_detections', 10)
        self._sub = self.create_subscription(Image, image_topic, self._on_image, 10)
        self._debug_pub = None
        if self._publish_debug:
            self._debug_pub = self.create_publisher(Image, '/victim_detector/debug_image', 1)

        self.get_logger().info(
            f'victim_detector: DNN person detector on {image_topic} '
            f'(conf>{self._conf})')

    def _on_image(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        result = detect_person(frame, self._net, conf_threshold=self._conf)

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
