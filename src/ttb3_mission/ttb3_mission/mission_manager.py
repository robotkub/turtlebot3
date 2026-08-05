#!/usr/bin/env python3
"""The mission 'brain'. A small hand-rolled state machine --
deliberately not smach/yasmin (neither is installed, and this team has no
prior ROS experience, so keep the control flow readable in plain Python).

Flow: IDLE -> INIT -> SEARCH -> APPROACH_VICTIM or DISPENSE (see decide_dispense)
-> DISPENSE -> back to SEARCH (next zone) -> ... -> RETURN_HOME -> DONE, with
STUCK and ESTOPPED safety detours that can happen from any active
state and resume where they left off.

Dispense rule (see docs/en/07-run-mission.md):
  - AprilTag seen          -> dispense tag.box_count immediately (-> DISPENSE)
  - Victim seen, no tag    -> dispense 1 box after walking up (-> APPROACH_VICTIM)
  Tag takes priority so a theoretical simultaneous sighting is deterministic.

Zone visiting (see zones.py, maps/mission_zones.yaml): SEARCH drives to each
zone on the list IN ORDER. Arriving at a zone with nothing to see just moves
on to the next one. A dispense doesn't end the run -- it returns to SEARCH
and continues with the next zone. RETURN_HOME only happens once every zone
on the list has been visited.

The robot boots into IDLE (armed but stationary) and only starts the run when
it gets a start signal (SW1 on the robot, or /mission_start from anywhere).
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
from std_msgs.msg import Bool, Empty, Int32
from tf_transformations import euler_from_quaternion, quaternion_from_euler

from ttb3_msgs.msg import MissionStatus, TagReading, VictimDetection
from ttb3_msgs.srv import ResetToStart, SaveStartPose

from .paths import start_pose_path, zones_path
from .start_pose import load_start_pose, save_start_pose
from .zones import load_zones

IDLE = 'IDLE'
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


def decide_dispense(tag, victim):
    """Pure decision function for the SEARCH -> dispense transition.

    Corrected rule (replaces the old "both tag AND victim simultaneously" check
    that could never fire against the real arena, where tag zones 2/3 and victim
    zones 1/5 are physically separate and TagReading.valid is not latched):

      - Tag seen (valid):            dispense tag.box_count immediately, skip the
                                     approach walk (go straight to DISPENSE).
      - Victim seen, no tag:         dispense 1 box after walking up to the sign
                                     (go to APPROACH_VICTIM — the servo still needs
                                     to be close and centered).
      - Neither:                     keep patrolling (return None).
      - Both (theoretical edge case; shouldn't happen per arena layout): tag wins
                                     (more specific signal, deterministic priority).

    Returns: (next_state: str, box_count: int) or None if nothing triggers.
    """
    if tag.valid:
        # Tag is the more specific signal — dispense its count right here,
        # no approach walk needed (tag gives count but not proximity bearing).
        return (DISPENSE, tag.box_count)
    if victim.detected:
        # Victim seen without a tag — drive up first, then dispense 1 box.
        return (APPROACH_VICTIM, 1)
    return None


class MissionManager(Node):

    def __init__(self):
        super().__init__('mission_manager')

        self.declare_parameter('tick_hz', 5.0)
        # Resolved at runtime, not hardcoded: this node runs both on the Pi
        # (~/turtlebot3_ws/maps) and in the laptop container (/maps). See
        # paths.py -- pinning these in mission_params.yaml is what made the
        # mission silently use its placeholder START and zones.
        self.declare_parameter('start_pose_file', start_pose_path())
        self.declare_parameter('zones_file', zones_path())
        self.declare_parameter('approach_bearing_gain', 0.8)
        self.declare_parameter('approach_linear_speed', 0.15)
        self.declare_parameter('approach_close_size', 0.20)
        self.declare_parameter('approach_center_tolerance', 0.15)
        self.declare_parameter('search_turn_rate', 0.3)
        self.declare_parameter('stuck_timeout_sec', 10.0)
        self.declare_parameter('stuck_min_progress_m', 0.05)

        self._start_pose_file = self.get_parameter('start_pose_file').value
        self._zones_file = self.get_parameter('zones_file').value
        self._zones = load_zones(self._zones_file)
        self._zone_idx = 0

        self._latest_tag = TagReading()
        self._latest_victim = VictimDetection()
        self._latest_amcl = None  # (x, y, yaw) or None until first /amcl_pose
        self._boxes_target = 0
        self._boxes_dispensed = 0
        self._estop_active = False
        self._pre_estop_state = IDLE
        self._pre_stuck_state = IDLE
        self._state = IDLE
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
        self.create_subscription(Empty, '/mission_start', self._on_mission_start, 10)
        self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self._on_amcl_pose, 10)

        self._cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self._initialpose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', latched)
        self._dispense_pub = self.create_publisher(Int32, '/dispense_command', 10)
        self._status_pub = self.create_publisher(MissionStatus, '/mission_status', 10)

        self.create_service(ResetToStart, 'reset_to_start', self._on_reset_to_start)
        self.create_service(SaveStartPose, 'save_start_pose', self._on_save_start_pose)

        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        tick_period = 1.0 / self.get_parameter('tick_hz').value
        self.create_timer(tick_period, self._tick)

        self.get_logger().info(
            'mission_manager: IDLE -- press SW1 (or publish /mission_start) to begin')

    # ---- subscriptions -----------------------------------------------

    def _on_tag(self, msg: TagReading):
        self._latest_tag = msg

    def _on_victim(self, msg: VictimDetection):
        self._latest_victim = msg

    def _on_boxes_remaining(self, msg: Int32):
        if self._dispense_waiting and msg.data == 0:
            self._dispense_waiting = False

    def _on_amcl_pose(self, msg: PoseWithCovarianceStamped):
        q = msg.pose.pose.orientation
        _, _, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])
        self._latest_amcl = (msg.pose.pose.position.x, msg.pose.pose.position.y, yaw)

    def _on_mission_start(self, _msg: Empty):
        if self._state == IDLE:
            self.get_logger().info('mission start received -- beginning run')
            self._state = INIT
        elif self._state == STUCK:
            # SW1 out of STUCK means "try again", which is what an operator
            # standing over a wedged robot is asking for. Previously this was
            # ignored ("SW1 ignored (mission already running, state=STUCK)")
            # and the only ways out were /reset_to_start or an e-stop cycle --
            # neither obvious with the robot in front of you.
            self.get_logger().info(
                f'retry requested -- resuming {self._pre_stuck_state} from STUCK')
            self._resume_state(self._pre_stuck_state)

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
        self._publish_initialpose(*self._read_start())
        if self._state == STUCK:
            self._resume_state(self._pre_stuck_state)
        self.get_logger().info('reset_to_start: re-localized to START pose, mission progress kept')
        response.success = True
        return response

    def _on_save_start_pose(self, request, response):
        if self._latest_amcl is None:
            self.get_logger().warning(
                'save_start_pose: no /amcl_pose received yet -- is AMCL running?')
            response.success = False
            return response
        x, y, yaw = self._latest_amcl
        save_start_pose(self._start_pose_file, x, y, yaw)
        self.get_logger().info(
            f'save_start_pose: wrote START = ({x:.3f}, {y:.3f}, {yaw:.3f}) '
            f'to {self._start_pose_file}')
        response.success = True
        response.x, response.y, response.yaw = float(x), float(y), float(yaw)
        return response

    # ---- helpers -------------------------------------------------------

    def _read_start(self):
        # Re-read on each use so a save_start_pose takes effect live.
        return load_start_pose(self._start_pose_file)

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
        # Start the stuck watchdog's window over. _odom_history fills from
        # /odom continuously, including all the time the robot sits parked in
        # IDLE -- so without this the history already holds a full
        # stuck_timeout_sec of not moving the instant we start driving, and
        # _is_stuck() fires immediately on the first goal. That is exactly
        # what happened on the first real run: SW1 -> "no progress for 10.0s
        # -- STUCK" 0.4 s later, goal cancelled, and every resume looped
        # straight back into STUCK because the stale history was still there.
        # A new goal is precisely the moment movement becomes expected.
        self._reset_progress_window()
        goal = NavigateToPose.Goal()
        goal.pose = _pose(x, y, yaw)
        future = self._nav_client.send_goal_async(goal)
        future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        handle = future.result()
        if handle is not None and handle.accepted:
            self._nav_goal_handle = handle
            # Subscribe to the RESULT too. Without this the handle was only
            # ever cleared by _cancel_nav_goal(), so after the first goal was
            # accepted _nav_goal_active() stayed True forever -- and every
            # "have we arrived yet?" check in _tick is written as
            # `if not self._nav_goal_active()`. The robot drove to zone 1,
            # Nav2 reported "Goal succeeded", and the mission then sat there:
            # it never advanced a zone, and RETURN_HOME could never reach
            # DONE. The stuck watchdog firing 10s later was the symptom, not
            # the cause.
            handle.get_result_async().add_done_callback(self._on_nav_result)

    def _on_nav_result(self, _future):
        # Succeeded, aborted or cancelled -- either way this goal is over and
        # the robot is no longer driving toward it. _tick decides what to do
        # next from the state; all that matters here is that we stop claiming
        # a goal is in flight.
        self._nav_goal_handle = None

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
            self._send_nav_goal(*self._zones[self._zone_idx])
        elif state == RETURN_HOME and not self._nav_goal_active():
            self._send_nav_goal(*self._read_start())

    def _advance_zone(self):
        """Move on from the current zone (whether it had nothing, or was just
        dispensed at) to the next one on the list -- RETURN_HOME once every
        zone has been visited (see zones.py, maps/mission_zones.yaml)."""
        self._zone_idx += 1
        if self._zone_idx < len(self._zones):
            self._state = SEARCH
            self._send_nav_goal(*self._zones[self._zone_idx])
        else:
            self._state = RETURN_HOME
            self._send_nav_goal(*self._read_start())

    def _reset_progress_window(self):
        """Forget odom collected before now, so the stuck watchdog needs a
        fresh stuck_timeout_sec of genuinely-not-moving before it fires."""
        self._odom_history = []

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

        # Only judge "stuck" when the robot is actually supposed to be moving.
        # SEARCH and RETURN_HOME move by driving a Nav2 goal, so with no goal
        # in flight the robot is legitimately parked -- sitting at a zone
        # looking for a tag is not being stuck. APPROACH_VICTIM drives itself
        # on /cmd_vel, so it is always expected to be moving.
        expected_to_move = (
            (self._state in (SEARCH, RETURN_HOME) and self._nav_goal_active())
            or self._state == APPROACH_VICTIM)
        if expected_to_move and self._is_stuck():
            self.get_logger().warning(f'no progress for {self.get_parameter("stuck_timeout_sec").value}s -- STUCK')
            self._pre_stuck_state = self._state
            self._cancel_nav_goal()
            self._cmd_vel_pub.publish(Twist())
            self._state = STUCK
            return

        if self._state == IDLE:
            pass  # armed but stationary until a start signal arrives

        elif self._state == INIT:
            self._publish_initialpose(*self._read_start())
            self._zone_idx = 0
            self._state = SEARCH
            self._send_nav_goal(*self._zones[self._zone_idx])

        elif self._state == SEARCH:
            decision = decide_dispense(self._latest_tag, self._latest_victim)
            if decision is not None:
                next_state, box_count = decision
                self._boxes_target = box_count
                self._cancel_nav_goal()
                self._state = next_state
                return
            if not self._nav_goal_active():
                # Arrived at this zone with nothing to see -- try the next one.
                self._advance_zone()

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
                # Dispensed at this zone -- move on to the next one (or home
                # if that was the last zone on the list).
                self._advance_zone()

        elif self._state == RETURN_HOME:
            if not self._nav_goal_active():
                self._state = DONE

        elif self._state == DONE:
            pass  # hold position, keep publishing status

        elif self._state == STUCK:
            pass  # wait for operator to reposition + call reset_to_start

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
