"""Servo-on-GPIO dispenser backend (R3/R5).

The dispenser is a hobby servo wired to a Pi GPIO pin. Angle convention (per
the team's mechanism):
    hold_angle  (0 deg)   = gate closed, cube held
    shoot_angle (180 deg) = gate flicks, one cube launched
One box = one hold -> shoot -> hold cycle.

gpiozero is imported lazily (only when this backend is actually selected) so it
stays an optional dependency -- the mock backend needs none of it. On Pi 5 you
also need the lgpio pin factory; gpiozero picks a working one automatically on
Pi 3/4. Both python3-gpiozero and python3-lgpio are installed by the pi branch
of install-humble-turtlebot3.sh.

A fake servo object can be injected (`servo=`) to unit-test the angle-cycle
logic with no hardware -- see the dispenser smoke test.
"""
import time

from .base import DispenserBackend


class GpioDispenserBackend(DispenserBackend):

    def __init__(self, logger, gate_pin: int = 18,
                 hold_angle: float = 0.0, shoot_angle: float = 180.0,
                 settle_time_sec: float = 0.7,
                 min_pulse_width_s: float = 0.0005,
                 max_pulse_width_s: float = 0.0025,
                 servo=None):
        self._logger = logger
        self._hold = hold_angle
        self._shoot = shoot_angle
        self._settle = settle_time_sec

        if servo is not None:
            # Injected fake for tests / bench runs without hardware.
            self._servo = servo
        else:
            # Lazy import: only real hardware runs pull gpiozero in.
            from gpiozero import AngularServo
            self._servo = AngularServo(
                gate_pin,
                min_angle=min(hold_angle, shoot_angle),
                max_angle=max(hold_angle, shoot_angle),
                min_pulse_width=min_pulse_width_s,
                max_pulse_width=max_pulse_width_s,
            )

        # Start closed so a boxed cube stays put.
        self._servo.angle = self._hold
        self._logger.info(
            f'GpioDispenserBackend ready on GPIO{gate_pin} '
            f'(hold={hold_angle} deg, shoot={shoot_angle} deg)')

    def dispense(self, count: int) -> int:
        dispensed = 0
        for i in range(max(0, count)):
            self._servo.angle = self._shoot
            time.sleep(self._settle)
            self._servo.angle = self._hold
            time.sleep(self._settle)
            dispensed += 1
            self._logger.info(f'dispensed cube {dispensed}/{count}')
        return dispensed

    def shutdown(self):
        # Detach so the servo isn't held under torque after the node exits.
        try:
            self._servo.detach()
        except AttributeError:
            pass
