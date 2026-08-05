"""Hardware-abstraction interface for whatever ends up physically dropping
boxes. The dispenser mechanism isn't decided yet, so dispenser_controller
talks to this interface only — swap in a real backend later without touching
the node or the mission-facing /dispense_command + /boxes_remaining topics."""
from abc import ABC, abstractmethod


class DispenserBackend(ABC):

    @abstractmethod
    def dispense(self, count: int) -> int:
        """Physically release `count` boxes. Returns how many were actually
        dispensed (may be less than requested if the hopper runs out)."""
        raise NotImplementedError

    def shutdown(self):
        """Optional cleanup hook (e.g. release GPIO lines). Default: no-op."""
        pass
