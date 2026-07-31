#!/usr/bin/env python3
"""The mission 'brain' (SRS Layer 5). A small hand-rolled state machine --
deliberately not smach/yasmin (neither is installed, and this team has no
prior ROS experience, so keep the control flow readable in plain Python).

Flow: INIT -> SEARCH -> APPROACH_VICTIM -> DISPENSE -> RETURN_HOME -> DONE,
with STUCK (R7) and ESTOPPED (R9) safety detours that can happen from any
active state and resume where they left off.
"""
import math
import time

import rclpy
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, Int32
from tf_transformations import quaternion_from_euler

from ttb3_msgs.msg import MissionStatus, TagReading, VictimDetection
from ttb3_msgs.srv import ResetToStart

INIT = 'INIT'
SEARCH = 'SEARCH'
APPROACH_VICTIM = 'APPROACH_VICTIM'
DISPENSE = 'DISPENSE'
RETURN_HOME = 'RETURN_HOME'
DONE = 'DONE'
STUCK = 'STUCK'
ESTOPPED = 'ESTOPPED'


def _pose(x, y, yaw, frame='map'):
    msg = PoseStamped()
    msg.header.frame_id = frame
    msg.pose.position.x = float(x)
    msg.pose.position.y = float(y)
    qx, qy, qz, qw = quaternion_from_euler(0, 0, float(yaw))
    msg.pose.orientation.x = qx
    msg.pose.orientation.y = qy
    msg.pose.orientation.z = qz
    msg.pose.orientation.w = qw
    return msg


class MissionManager(Node):

    def __init__(self):
        super().__init__('mission_manager')

        self.declare_parameter('tick_hz', 5.0)
        self.declare_parameter('start_x', 0.25)
        self.declare_parameter('start_y', 0.25)
        self.declare_parameter('start_yaw', 0.0)
        self.declare_parameter('waypoints_x', [0.5, 1.5, 1.5, 0.5])
        self.declare_parameter('waypoints_y', [0.5, 0.5, 1.5, 1.5])
        self.declare_parameter('waypoints_yaw', [0.0, 1.57, 3.14, -1.57])
        self.declare_parameter('approach_bearing_gain', 0.8)
        self.declare_parameter('approach_linear_speed', 0.15)
        self.declare_parameter('approach_close_size', 0.20)
        self.declare_parameter('approach_center_tolerance', 0.15)
        self.declare_parameter('search_turn_rate', 0.3)
        self.declare_parameter('stuck_timeout_sec', 10.0)
        self.declare_parameter('stuck_min_progress_m', 0.05)

        self._start_pose = (
            self.get_parameter('start_x').value,
            self.get_parameter('start_y').value,
            self.get_parameter('start_yaw').value,
        )
        self._waypoints = list(zip(
            self.get_parameter('waypoints_x').value,
            self.get_parameter('waypoints_y').value,
            self.get_parameter('waypoints_yaw').value,
        ))
        self._waypoint_idx = 0

        self._latest_tag = TagReading()
        self._latest_victim = VictimDetection()
        self._boxes_target = 0
        self._boxes_dispensed = 0
        self._estop_active = False
        self._pre_estop_state = INIT
        self._pre_stuck_state = INIT
        self._state = INIT
        self._nav_goal_handle = None
        self._dispense_sent = False
        self._dispense_waiting = False

        self._odom_history = []  # list of (monotonic_time, x, y)

        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

        self.create_subscription(TagReading, '/tag_detections', self._on_tag, 10)
        self.create_subscription(VictimDetection, '/victim_detections', self._on_victim, 10)
        self.create_subscription(Odometry, '/odom', self._on_odom, 10)
        self.create_subscription(Int32, '/boxes_remaining', self._on_boxes_remaining, 10)
        self.create_subscription(Bool, '/estop_active', self._on_estop, latched)

        self._cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self._initialpose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', latched)
        self._dispense_pub = self.create_publisher(Int32, '/dispense_command', 10)
        self._status_pub = self.create_publisher(MissionStatus, '/mission_status', 10)

        self.create_service(ResetToStart, 'reset_to_start', self._on_reset_to_start)

        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        tick_period = 1.0 / self.get_parameter('tick_hz').value
        self.create_timer(tick_period, self._tick)

        self.get_logger().info('mission_manager: starting in INIT')

    # ---- subscriptions -----------------------------------------------

    def _on_tag(self, msg: TagReading):
        self._latest_tag = msg

    def _on_victim(self, msg: VictimDetection):
        self._latest_victim = msg

    def _on_boxes_remaining(self, msg: Int32):
        if self._dispense_waiting and msg.data == 0:
            self._dispense_waiting = False

    def _on_estop(self, msg: Bool):
        if msg.data and not self._estop_active:
            self._pre_estop_state = self._state
            self._cancel_nav_goal()
            self._state = ESTOPPED
        elif not msg.data and self._estop_active:
            self._resume_state(self._pre_estop_state)
        self._estop_active = msg.data

    def _on_odom(self, msg: Odometry):
        now = time.monotonic()
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        self._odom_history.append((now, x, y))
        cutoff = now - self.get_parameter('stuck_timeout_sec').value
        self._odom_history = [(t, px, py) for (t, px, py) in self._odom_history if t >= cutoff]

    def _on_reset_to_start(self, request, response):
        self._publish_initialpose(*self._start_pose)
        if self._state == STUCK:
            self._resume_state(self._pre_stuck_state)
        self.get_logger().info('reset_to_start: re-localized to START pose, mission progress kept')
        response.success = True
        return response

    # ---- helpers -------------------------------------------------------

    def _publish_initialpose(self, x, y, yaw):
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = 'map'
        msg.pose.pose.position.x = float(x)
        msg.pose.pose.position.y = float(y)
        qx, qy, qz, qw = quaternion_from_euler(0, 0, float(yaw))
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        self._initialpose_pub.publish(msg)

    def _send_nav_goal(self, x, y, yaw):
        if not self._nav_client.server_is_ready():
            return
        goal = NavigateToPose.Goal()
        goal.pose = _pose(x, y, yaw)
        future = self._nav_client.send_goal_async(goal)
        future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        handle = future.result()
        if handle is not None and handle.accepted:
            self._nav_goal_handle = handle

    def _cancel_nav_goal(self):
        if self._nav_goal_handle is not None:
            self._nav_goal_handle.cancel_goal_async()
            self._nav_goal_handle = None

    def _nav_goal_active(self):
        return self._nav_goal_handle is not None

    def _resume_state(self, state):
        # Re-entering SEARCH/RETURN_HOME needs a fresh nav goal -- the old one
        # was cancelled going into STUCK/ESTOPPED. APPROACH_VICTIM/DISPENSE
        # don't hold a nav goal, so they just pick back up next tick.
        self._state = state
        if state == SEARCH and not self._nav_goal_active():
            self._send_nav_goal(*self._waypoints[self._waypoint_idx])
        elif state == RETURN_HOME and not self._nav_goal_active():
            self._send_nav_goal(*self._start_pose)

    def _is_stuck(self):
        if len(self._odom_history) < 2:
            return False
        window = self.get_parameter('stuck_timeout_sec').value
        oldest_t = self._odom_history[0][0]
        if time.monotonic() - oldest_t < window:
            return False  # haven't been driving long enough yet to judge
        xs = [p[1] for p in self._odom_history]
        ys = [p[2] for p in self._odom_history]
        spread = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        return spread < self.get_parameter('stuck_min_progress_m').value

    def _publish_status(self):
        msg = MissionStatus()
        msg.state = self._state
        msg.boxes_dispensed = self._boxes_dispensed
        msg.boxes_target = self._boxes_target
        msg.estop_active = self._estop_active
        self._status_pub.publish(msg)

    # ---- main loop -------------------------------------------------------

    def _tick(self):
        self._publish_status()

        if self._estop_active:
            return  # button_handler already zeroed /cmd_vel and cancelled nav

        if self._state in (SEARCH, APPROACH_VICTIM, RETURN_HOME) and self._is_stuck():
            self.get_logger().warning(f'no progress for {self.get_parameter("stuck_timeout_sec").value}s -- STUCK')
            self._pre_stuck_state = self._state
            self._cancel_nav_goal()
            self._cmd_vel_pub.publish(Twist())
            self._state = STUCK
            return

        if self._state == INIT:
            self._publish_initialpose(*self._start_pose)
            self._state = SEARCH
            self._send_nav_goal(*self._waypoints[self._waypoint_idx])

        elif self._state == SEARCH:
            if self._latest_tag.valid and self._latest_victim.detected:
                self._boxes_target = self._latest_tag.box_count
                self._cancel_nav_goal()
                self._state = APPROACH_VICTIM
                return
            if not self._nav_goal_active():
                self._waypoint_idx = (self._waypoint_idx + 1) % len(self._waypoints)
                self._send_nav_goal(*self._waypoints[self._waypoint_idx])

        elif self._state == APPROACH_VICTIM:
            self._servo_to_victim()

        elif self._state == DISPENSE:
            if not self._dispense_sent:
                self._dispense_pub.publish(Int32(data=self._boxes_target))
                self._dispense_sent = True
                self._dispense_waiting = True
            elif not self._dispense_waiting:
                # _on_boxes_remaining flipped this False once boxes hit 0
                self._boxes_dispensed += self._boxes_target
                self._dispense_sent = False
                self._state = RETURN_HOME
                self._send_nav_goal(*self._start_pose)

        elif self._state == RETURN_HOME:
            if not self._nav_goal_active():
                self._state = DONE

        elif self._state == DONE:
            pass  # hold position, keep publishing status

        elif self._state == STUCK:
            pass  # wait for operator to reposition + press SW1 (reset_to_start)

    def _servo_to_victim(self):
        victim = self._latest_victim
        if not victim.detected:
            twist = Twist()
            twist.angular.z = self.get_parameter('search_turn_rate').value
            self._cmd_vel_pub.publish(twist)
            return

        close_enough = victim.apparent_size >= self.get_parameter('approach_close_size').value
        centered = abs(victim.bearing) <= self.get_parameter('approach_center_tolerance').value
        if close_enough and centered:
            self._cmd_vel_pub.publish(Twist())
            self._state = DISPENSE
            return

        twist = Twist()
        twist.angular.z = -self.get_parameter('approach_bearing_gain').value * victim.bearing
        target_size = self.get_parameter('approach_close_size').value
        twist.linear.x = max(0.0, self.get_parameter('approach_linear_speed').value
                              * (1.0 - victim.apparent_size / target_size))
        self._cmd_vel_pub.publish(twist)


def main():
    rclpy.init()
    node = MissionManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
