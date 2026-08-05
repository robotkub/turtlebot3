"""Record mission zones without hand-editing YAML.

The zone list (maps/mission_zones.yaml) decides where the robot goes during
SEARCH. Typing coordinates into it by hand means reading them off a map by
eye, which is exactly the step that goes wrong quietly. This node lets you
record them from Foxglove instead:

    1. Pick the point tool in the 3D panel and click a spot on the map --
       Foxglove publishes it on /clicked_point.
    2. Press "Save mission point" (a Call Service button on /save_zone).

or, when the heading matters, drive the robot to the spot and save with
source "robot", which takes the live /amcl_pose including its yaw.

Why a separate node rather than more services on mission_manager: recording
zones is something you do while looking at a map in a `./ttb3 nav` session,
and mission_manager only runs under debug/competition.launch.py. This runs in
both.

mission_manager reads the zone file once at startup, so a zone saved mid-run
applies from its next start -- the service says so in its reply rather than
letting you assume it took effect immediately.
"""
import rclpy
from geometry_msgs.msg import PointStamped, PoseWithCovarianceStamped
from rclpy.node import Node
from std_srvs.srv import Trigger
from tf_transformations import euler_from_quaternion

from ttb3_msgs.srv import SaveZone

from .paths import zones_path
from .zones import append_zone, read_zones, save_zones


class ZoneRecorder(Node):
    def __init__(self):
        super().__init__('zone_recorder')
        self.declare_parameter('zones_file', zones_path())
        self._zones_file = self.get_parameter('zones_file').value

        self._last_click = None   # (x, y) from Foxglove's point tool
        self._last_pose = None    # (x, y, yaw) from AMCL

        self.create_subscription(
            PointStamped, 'clicked_point', self._on_click, 10)
        self.create_subscription(
            PoseWithCovarianceStamped, 'amcl_pose', self._on_pose, 10)

        self.create_service(SaveZone, 'save_zone', self._on_save_zone)
        self.create_service(Trigger, 'clear_zones', self._on_clear_zones)

        self.get_logger().info(
            f'zone_recorder ready -- zones file: {self._zones_file} '
            f'({len(read_zones(self._zones_file))} zones now). '
            'Click the map in Foxglove, then call /save_zone.')

    def _on_click(self, msg):
        self._last_click = (msg.point.x, msg.point.y)
        self.get_logger().info(
            f'clicked point ({msg.point.x:.3f}, {msg.point.y:.3f}) -- '
            'call /save_zone to keep it')

    def _on_pose(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        _, _, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])
        self._last_pose = (p.x, p.y, yaw)

    def _on_save_zone(self, request, response):
        source = (request.source or 'click').strip().lower()

        if source == 'click':
            if self._last_click is None:
                response.success = False
                response.message = (
                    'no point clicked yet -- pick the point tool in '
                    "Foxglove's 3D panel and click the map first")
                return response
            x, y = self._last_click
            yaw = float(request.yaw)
        elif source == 'robot':
            if self._last_pose is None:
                response.success = False
                response.message = (
                    'no /amcl_pose received yet -- is AMCL running and '
                    'localized?')
                return response
            x, y, yaw = self._last_pose
        else:
            response.success = False
            response.message = (
                f"unknown source '{request.source}' -- use 'click' or 'robot'")
            return response

        try:
            zones = append_zone(self._zones_file, x, y, yaw)
        except OSError as exc:
            response.success = False
            response.message = f'could not write {self._zones_file}: {exc}'
            self.get_logger().error(response.message)
            return response

        response.success = True
        response.count = len(zones)
        response.x, response.y, response.yaw = float(x), float(y), float(yaw)
        response.message = (
            f'saved zone {len(zones)} at ({x:.3f}, {y:.3f}, {yaw:.3f}) '
            '-- restart mission_manager to use it')
        self.get_logger().info(response.message)
        return response

    def _on_clear_zones(self, request, response):
        del request
        try:
            save_zones(self._zones_file, [])
        except OSError as exc:
            response.success = False
            response.message = f'could not write {self._zones_file}: {exc}'
            self.get_logger().error(response.message)
            return response
        response.success = True
        response.message = (
            'zone list emptied -- note mission_manager falls back to its four '
            'DEFAULT_ZONES placeholders while the list is empty')
        self.get_logger().warning(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ZoneRecorder()
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
