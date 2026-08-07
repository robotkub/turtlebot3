#!/usr/bin/env python3
"""Wraps apriltag_ros's raw detections into the simplified TagReading contract
that mission_manager consumes on /tag_detections."""
import rclpy
from rclpy.node import Node
from apriltag_msgs.msg import AprilTagDetectionArray

from ttb3_msgs.msg import TagReading

from .vision_core import corner_area, tag_id_to_box_count


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
        # Last (valid, tag_id, box_count) actually logged. Detections publish
        # at camera rate, so logging every one would scroll the answer off the
        # screen faster than anyone can read it -- see _publish.
        self._last_logged = None
        self._watchdog = self.create_timer(stale_timeout, self._on_watchdog)
        self._got_message_since_watchdog = False

        self.get_logger().info(
            f'apriltag_detector: listening on {raw_topic}, republishing on /tag_detections')

    def _on_detections(self, msg: AprilTagDetectionArray):
        self._got_message_since_watchdog = True
        if not msg.detections:
            self._publish(valid=False, tag_id=0)
            return

        closest = max(
            msg.detections,
            key=lambda d: corner_area([(c.x, c.y) for c in d.corners]))
        box_count = tag_id_to_box_count(closest.id, self._offset, self._max_count)
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

        # Say the answer out loud, edge-triggered. `./ttb3 detect` exists to
        # answer "does it see the tag, and how many boxes is that?" -- having
        # to run a second terminal and echo a topic to find out defeats the
        # point. Only on CHANGE, because this publishes at camera rate.
        state = (valid, tag_id, box_count)
        if state != self._last_logged:
            self._last_logged = state
            if valid:
                self.get_logger().info(
                    f'TAG {tag_id}  ->  {box_count} box'
                    f'{"" if box_count == 1 else "es"}')
            else:
                self.get_logger().info('no tag in view')


def main():
    rclpy.init()
    node = AprilTagDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl-C: the signal handler has already torn the context down, so
        # spin() unwinds through here. Without this, the KeyboardInterrupt
        # propagates and launch reports a clean stop as "process has died,
        # exit code 1" -- which makes a real crash indistinguishable from a
        # normal shutdown. Matches zone_recorder/map_autosaver.
        pass
    finally:
        node.destroy_node()
        # Same reason: rclpy.shutdown() on an already-shut-down context raises
        # RCLError("rcl_shutdown already called").
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
