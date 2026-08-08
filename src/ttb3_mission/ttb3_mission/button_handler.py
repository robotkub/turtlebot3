#!/usr/bin/env python3
"""Watches the two OpenCR push buttons and turns them
into mission control signals.

Only two physical buttons exist, so SW1 is context-sensitive:

  SW1 (BUTTON0):
    - if e-stopped   -> RESUME (clear the e-stop latch)
    - elif IDLE      -> START the mission (/mission_start)
    - otherwise      -> ignored (mission already running)
  SW2 (BUTTON1):
    - E-STOP: zero /cmd_vel and cancel all Nav2 goals directly (doesn't
      round-trip through mission_manager, so it stays inside the 200 ms
      budget), and latch /estop_active so mission_manager pauses.

Re-localizing to START (reset_to_start) is now a service call (from Foxglove
or the CLI), not a button -- the two buttons are needed for start/stop/resume.

The same two actions are also exposed as services, so Foxglove (or a laptop
with no line of sight to the robot) can drive them:

  /start_mission (std_srvs/Trigger) -> identical to pressing SW1
  /estop         (std_srvs/Trigger) -> identical to pressing SW2

They deliberately call the SAME handlers as the physical buttons rather than
reimplementing the logic, so the two paths cannot drift apart.

These are services, NOT topics, for a specific reason: /estop_active is
published TRANSIENT_LOCAL (so a late-joining mission_manager still learns the
latch state), and foxglove_bridge advertises client-published topics as
VOLATILE. A volatile publisher is QoS-INCOMPATIBLE with a transient_local
subscriber, so a Foxglove "Publish" panel aimed at /estop_active would connect
to nothing and silently do nothing -- the worst possible failure for a stop
button. A service call has no durability to mismatch, and it returns a
success flag the operator can actually see.

NOTE: this assumes CUSTOM OpenCR firmware where SW1/SW2 only report state on
/sensor_state. Stock ROBOTIS firmware also test-drives the robot on these
buttons (SW1 = forward 0.3 m, SW2 = spin 180) -- see firmware/opencr/.
"""
import rclpy
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, Empty
from std_srvs.srv import Trigger
from turtlebot3_msgs.msg import SensorState

from ttb3_msgs.msg import MissionStatus

BUTTON0 = SensorState.BUTTON0  # SW1
BUTTON1 = SensorState.BUTTON1  # SW2


class ButtonHandler(Node):

    def __init__(self):
        super().__init__('button_handler')
        self._prev_button = 0
        self._estop_active = False
        self._mission_state = 'IDLE'

        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self._estop_pub = self.create_publisher(Bool, '/estop_active', latched)
        self._start_pub = self.create_publisher(Empty, '/mission_start', 10)
        self._cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self._cancel_client = self.create_client(CancelGoal, '/navigate_to_pose/_action/cancel_goal')

        self.create_subscription(SensorState, '/sensor_state', self._on_sensor_state, 10)
        self.create_subscription(MissionStatus, '/mission_status', self._on_status, 10)

        # Foxglove's Start/Stop buttons. Same handlers as SW1/SW2 -- see the
        # module docstring for why these are services and not topics.
        self.create_service(Trigger, 'start_mission', self._srv_start)
        self.create_service(Trigger, 'estop', self._srv_estop)

        # Define /estop_active from boot so late subscribers (mission_manager) don't
        # start in an ambiguous state.
        self._estop_pub.publish(Bool(data=False))
        self.get_logger().info('button_handler ready (SW1=start/resume, SW2=e-stop)')

    def _on_status(self, msg: MissionStatus):
        self._mission_state = msg.state
        self._estop_active = msg.estop_active

    def _on_sensor_state(self, msg: SensorState):
        newly_pressed = msg.button & ~self._prev_button
        if newly_pressed & BUTTON0:
            self._handle_sw1()
        if newly_pressed & BUTTON1:
            self._handle_sw2()
        self._prev_button = msg.button

    def _handle_sw1(self):
        if self._estop_active:
            self.get_logger().info('SW1: RESUME (clearing e-stop)')
            self._estop_pub.publish(Bool(data=False))
        elif self._mission_state == 'IDLE':
            self.get_logger().info('SW1: START mission')
            self._start_pub.publish(Empty())
        elif self._mission_state == 'STUCK':
            # mission_manager's /mission_start handler treats STUCK
            # specially -- it's a "retry from here" signal, not a fresh
            # start (see mission_manager.py _on_mission_start). Without this
            # branch SW1 fell into the "ignored" case below forever: clearing
            # an e-stop only ever restores whatever state was active when the
            # e-stop was hit, so an e-stop pressed while STUCK resumes right
            # back into STUCK, and from there this was the only button that
            # was ever supposed to get the operator out.
            self.get_logger().info('SW1: retry from STUCK')
            self._start_pub.publish(Empty())
        else:
            self.get_logger().info(
                f'SW1 ignored (mission already running, state={self._mission_state})')

    def _handle_sw2(self):
        self.get_logger().warning('SW2 pressed: E-STOP')
        self._cmd_vel_pub.publish(Twist())
        self._estop_pub.publish(Bool(data=True))
        self._cancel_all_nav_goals()

    def _srv_start(self, _request, response):
        # Report what SW1 actually decided to do, so the operator is not left
        # guessing whether a press in the wrong state did anything.
        if self._estop_active:
            action = 'RESUME (e-stop cleared)'
        elif self._mission_state == 'IDLE':
            action = 'START'
        elif self._mission_state == 'STUCK':
            action = 'RETRY (resuming from STUCK)'
        else:
            action = f'ignored -- mission already running (state={self._mission_state})'
        self._handle_sw1()
        response.success = 'ignored' not in action
        response.message = action
        return response

    def _srv_estop(self, _request, response):
        self._handle_sw2()
        response.success = True
        response.message = 'E-STOP latched, cmd_vel zeroed, nav goals cancelled'
        return response

    def _cancel_all_nav_goals(self):
        if not self._cancel_client.service_is_ready():
            return
        # A zero-filled goal_id + zero timestamp means "cancel every active
        # goal" per action_msgs/srv/CancelGoal semantics -- the default
        # constructed request already zero-fills both.
        self._cancel_client.call_async(CancelGoal.Request())


def main():
    rclpy.init()
    node = ButtonHandler()
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
