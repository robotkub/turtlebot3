#!/usr/bin/env python3
"""Drives the supply-box dispenser against a swappable hardware
backend. Mission-facing contract is the plain topic pair /dispense_command
in, /boxes_remaining out. The backend itself is
selected by the use_mock_hardware param -- see hardware/base.py."""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32

from .hardware.mock_backend import MockDispenserBackend


class DispenserController(Node):

    def __init__(self):
        super().__init__('dispenser_controller')

        self.declare_parameter('use_mock_hardware', True)
        self.declare_parameter('gate_pin', 18)
        # Real-mechanism calibration -- see config/dispenser.yaml, which is
        # what actually feeds these when launched via hardware.launch.py.
        # Kept in sync here too since `ros2 run` directly (no launch file)
        # skips the yaml entirely.
        self.declare_parameter('hold_angle', 180.0)
        self.declare_parameter('shoot_angle', 120.0)
        self.declare_parameter('settle_time_sec', 0.7)

        use_mock = self.get_parameter('use_mock_hardware').value
        self._backend = self._make_backend(use_mock)

        self._remaining_pub = self.create_publisher(Int32, '/boxes_remaining', 10)
        self.create_subscription(Int32, '/dispense_command', self._on_dispense_command, 10)

        self.get_logger().info(
            f"dispenser_controller ready (backend={'mock' if use_mock else 'gpio'})")

    def _make_backend(self, use_mock: bool):
        if use_mock:
            return MockDispenserBackend(self.get_logger())

        # Deliberately not caught: a misconfigured real dispenser should fail
        # loudly at startup, not silently fall back to the mock mid-competition.
        from .hardware.gpio_backend import GpioDispenserBackend
        return GpioDispenserBackend(
            self.get_logger(),
            gate_pin=self.get_parameter('gate_pin').value,
            hold_angle=self.get_parameter('hold_angle').value,
            shoot_angle=self.get_parameter('shoot_angle').value,
            settle_time_sec=self.get_parameter('settle_time_sec').value,
        )

    def _on_dispense_command(self, msg: Int32):
        requested = msg.data
        dispensed = self._backend.dispense(requested)
        remaining = max(0, requested - dispensed)
        self._remaining_pub.publish(Int32(data=remaining))
        if remaining > 0:
            self.get_logger().warning(
                f'dispenser only dropped {dispensed}/{requested} boxes, {remaining} remaining')

    def destroy_node(self):
        self._backend.shutdown()
        super().destroy_node()


def main():
    rclpy.init()
    node = DispenserController()
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
