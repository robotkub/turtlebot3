"""Default backend while the real dispenser mechanism is undecided. Logs the
drop and reports success instantly -- lets mission_manager / dispenser_controller
be developed and tested with no hardware attached at all."""
from .base import DispenserBackend


class MockDispenserBackend(DispenserBackend):

    def __init__(self, logger):
        self._logger = logger

    def dispense(self, count: int) -> int:
        self._logger.info(f'[mock dispenser] would drop {count} box(es) now')
        return count
