#!/usr/bin/env python3
"""Wraps apriltag_ros's raw detections into the simplified TagReading contract
that mission_manager consumes on /tag_detections (see SRS section 4/5, R2/R3)."""
import rclpy
from rclpy.node import Node
from apriltag_msgs.msg import AprilTagDetectionArray

from ttb3_msgs.msg import TagReading


def _corner_area(corners):
    # Shoelace formula over the 4 tag corners -> pixel^2 area, used to pick the
    # closest/largest tag when several are visible at once.
    area = 0.0
    n = len(corners)
    for i in range(n):
        x1, y1 = corners[i].x, corners[i].y
        x2, y2 = corners[(i + 1) % n].x, corners[(i + 1) % n].y
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


class AprilTagDetector(Node):

    def __init__(self):
        super().__init__('apriltag_detector')

        self.declare_parameter('raw_detections_topic', '/apriltag/detections')
        self.declare_parameter('box_count_offset', 0)
        self.declare_parameter('max_box_count', 5)
        self.declare_parameter('stale_timeout_sec', 0.5)

        raw_topic = self.get_parameter('raw_detections_topic').value
        self._offset = self.get_parameter('box_count_offset').value
        self._max_count = self.get_parameter('max_box_count').value
        stale_timeout = self.get_parameter('stale_timeout_sec').value

        self._pub = self.create_publisher(TagReading, '/tag_detections', 10)
        self._sub = self.create_subscription(
            AprilTagDetectionArray, raw_topic, self._on_detections, 10)

        self._last_valid = False
        self._watchdog = self.create_timer(stale_timeout, self._on_watchdog)
        self._got_message_since_watchdog = False

        self.get_logger().info(
            f'apriltag_detector: listening on {raw_topic}, republishing on /tag_detections')

    def _on_detections(self, msg: AprilTagDetectionArray):
        self._got_message_since_watchdog = True
        if not msg.detections:
            self._publish(valid=False, tag_id=0)
            return

        closest = max(msg.detections, key=lambda d: _corner_area(d.corners))
        box_count = max(0, min(self._max_count, closest.id + self._offset))
        self._publish(valid=True, tag_id=closest.id, box_count=box_count)

    def _on_watchdog(self):
        # apriltag_ros publishes an (possibly empty) array on every camera
        # frame, so this only fires if the driver/detector has stalled outright.
        if not self._got_message_since_watchdog and self._last_valid:
            self._publish(valid=False, tag_id=0)
        self._got_message_since_watchdog = False

    def _publish(self, valid, tag_id, box_count=0):
        self._last_valid = valid
        out = TagReading()
        out.valid = valid
        out.tag_id = tag_id
        out.box_count = box_count
        self._pub.publish(out)


def main():
    rclpy.init()
    node = AprilTagDetector()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
