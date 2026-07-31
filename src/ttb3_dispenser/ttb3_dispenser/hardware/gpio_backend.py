"""Stub for a servo-on-GPIO dispenser backend. NOT wired up yet -- the physical
dispenser mechanism (servo trapdoor? stepper? relay?) hasn't been decided, so
this deliberately raises until someone fills in the real servo angles/timing.

gpiozero is imported lazily (only when this backend is actually selected) so it
stays an optional dependency -- the mock backend needs none of this to run.

TODO once the mechanism is chosen:
  - `pip install`/apt-install `python3-gpiozero` on the Pi (not installed today)
  - set `gate_pin` to the real BCM pin the servo signal wire is on
  - set `closed_angle` / `open_angle` to the measured trapdoor positions
  - tune `settle_time_sec` to how long the gate needs to swing + a box to fall
"""
from .base import DispenserBackend


class GpioDispenserBackend(DispenserBackend):

    def __init__(self, logger, gate_pin: int = 18,
                 closed_angle: float = 0.0, open_angle: float = 90.0,
                 settle_time_sec: float = 0.5):
        raise NotImplementedError(
            'GpioDispenserBackend is a stub -- the dispenser hardware design '
            '(servo pin, gate angles, timing) is not finalized yet. Use '
            "use_mock_hardware:=true until it is, then fill in this backend."
        )

    def dispense(self, count: int) -> int:  # pragma: no cover - unreachable stub
        raise NotImplementedError
