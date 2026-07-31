#!/usr/bin/env python3
"""Watches the two OpenCR push buttons (SRS section 8, R8/R9).

SW1 (BUTTON0): reset localization to START, keep mission progress, clear e-stop.
SW2 (BUTTON1): e-stop -- zero /cmd_vel and cancel all Nav2 goals directly
(doesn't round-trip through mission_manager, so it stays inside the 200ms
budget in R9), and latch /estop_active so mission_manager pauses.
"""
import rclpy
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile
from std_msgs.msg import Bool
from turtlebot3_msgs.msg import SensorState

from ttb3_msgs.srv import ResetToStart

BUTTON0 = SensorState.BUTTON0  # SW1
BUTTON1 = SensorState.BUTTON1  # SW2


class ButtonHandler(Node):

    def __init__(self):
        super().__init__('button_handler')
        self._prev_button = 0

        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self._estop_pub = self.create_publisher(Bool, '/estop_active', latched)
        self._cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self._cancel_client = self.create_client(CancelGoal, '/navigate_to_pose/_action/cancel_goal')
        self._reset_client = self.create_client(ResetToStart, 'reset_to_start')

        self.create_subscription(SensorState, '/sensor_state', self._on_sensor_state, 10)

        # Define /estop_active from boot so late subscribers (mission_manager) don't
        # start in an ambiguous state.
        self._estop_pub.publish(Bool(data=False))
        self.get_logger().info('button_handler ready (SW1=reset, SW2=e-stop)')

    def _on_sensor_state(self, msg: SensorState):
        newly_pressed = msg.button & ~self._prev_button
        if newly_pressed & BUTTON0:
            self._handle_sw1()
        if newly_pressed & BUTTON1:
            self._handle_sw2()
        self._prev_button = msg.button

    def _handle_sw1(self):
        self.get_logger().info('SW1 pressed: reset to START pose (mission progress kept)')
        if self._reset_client.service_is_ready():
            self._reset_client.call_async(ResetToStart.Request())
        else:
            self.get_logger().warning('reset_to_start service not available yet')
        self._estop_pub.publish(Bool(data=False))

    def _handle_sw2(self):
        self.get_logger().warning('SW2 pressed: E-STOP')
        self._cmd_vel_pub.publish(Twist())
        self._estop_pub.publish(Bool(data=True))
        self._cancel_all_nav_goals()

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
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
