"""Servo-on-GPIO dispenser backend.

The dispenser is a hobby servo wired to a Pi GPIO pin. Angle convention (per
the team's mechanism -- actual calibrated values live in
config/dispenser.yaml, not here):
    hold_angle   = gate closed, cube held (180 deg on the real mechanism)
    shoot_angle  = gate flicks, one cube launched (120 deg)
One box = one hold -> shoot -> hold cycle.

gpiozero is imported lazily (only when this backend is actually selected) so it
stays an optional dependency -- the mock backend needs none of it. Both
python3-gpiozero and python3-lgpio are installed by the pi branch of
install-humble-turtlebot3.sh.

The pin factory is pinned to pigpio rather than left to gpiozero's own search.
Its default order tries rpigpio first, and with RPi.GPIO absent (as it is on
Ubuntu 22.04 arm64) it falls all the way through to the `native` factory, which
cannot do PWM at all -- the node then died on startup with
`gpiozero.exc.PinPWMUnsupported: PWM is not supported on pin GPIO18` even
though a working pin factory was available.

Started on lgpio (software PWM) and switched to pigpio after the gate
visibly jittered while holding a position -- confirmed on the real servo
2026-08-08. pigpio's daemon isn't in this release's apt repo
(`apt-cache policy pigpio` -> none, only the `python3-pigpio` CLIENT is
packaged), so `pigpiod` is built from source and run as a systemd service
(see scripts/systemd/pigpiod.service, installed by
install-humble-turtlebot3.sh) -- this backend just needs it already running
and reachable on localhost:8888, gpiozero's default. If it ever isn't
(`systemctl status pigpiod`), AngularServo() raises immediately at startup
rather than silently falling back to a jittery factory.

A fake servo object can be injected (`servo=`) to unit-test the angle-cycle
logic with no hardware -- see the dispenser smoke test.
"""
import os
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
            # Must be set BEFORE gpiozero is imported -- it resolves its pin
            # factory at import time. An explicit override is respected.
            os.environ.setdefault('GPIOZERO_PIN_FACTORY', 'pigpio')
            # Lazy import: only real hardware runs pull gpiozero in.
            from gpiozero import AngularServo
            # initial_angle MUST be given explicitly: AngularServo's own
            # default is 0 deg, validated against min_angle/max_angle at
            # construction time -- fine when hold/shoot straddled 0, but
            # this backend's own hold_angle can sit outside [0, shoot] (the
            # real mechanism calibrated to hold=180/shoot=120, both >0), and
            # the unconditional 0 default raised
            # `OutputDeviceBadValue: AngularServo angle must be between
            # 120.0 and 180.0` before the constructor even returned --
            # confirmed on the real servo 2026-08-08.
            self._servo = AngularServo(
                gate_pin,
                initial_angle=hold_angle,
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
