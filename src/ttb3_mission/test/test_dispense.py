"""Unit tests for ttb3_mission.mission_manager.decide_dispense().

These run WITHOUT ROS — pure Python. No rclpy, no node spinning needed.
Mirror the style of src/ttb3_perception/test/test_vision.py (ROS-free).

Run locally:
    pytest src/ttb3_mission/test/test_dispense.py -v

Or via colcon (if a ROS workspace is sourced):
    colcon test --packages-select ttb3_mission
    colcon test-result --verbose
"""
import sys
import os
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock every ROS module that mission_manager.py imports at module level.
# decide_dispense() itself uses no ROS APIs, so a blanket MagicMock is fine.
# This must happen BEFORE the ttb3_mission import below.
# ---------------------------------------------------------------------------
_ROS_MOCKS = [
    'rclpy', 'rclpy.node', 'rclpy.action', 'rclpy.qos',
    'rclpy.executors', 'rclpy.callback_groups',
    'geometry_msgs', 'geometry_msgs.msg',
    'nav_msgs', 'nav_msgs.msg',
    'nav2_msgs', 'nav2_msgs.action',
    'action_msgs', 'action_msgs.msg',
    'std_msgs', 'std_msgs.msg',
    'turtlebot3_msgs', 'turtlebot3_msgs.msg',
    'ttb3_msgs', 'ttb3_msgs.msg', 'ttb3_msgs.srv',
    'tf_transformations',
]
for _mod in _ROS_MOCKS:
    sys.modules[_mod] = MagicMock()

# Make the package importable without a full colcon install.
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from ttb3_mission.mission_manager import APPROACH_VICTIM, DISPENSE, decide_dispense  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal stub messages — no ROS needed
# ---------------------------------------------------------------------------

class _Tag:
    """Minimal stand-in for ttb3_msgs.msg.TagReading."""
    def __init__(self, valid=False, box_count=0):
        self.valid = valid
        self.box_count = box_count


class _Victim:
    """Minimal stand-in for ttb3_msgs.msg.VictimDetection."""
    def __init__(self, detected=False):
        self.detected = detected


# ---------------------------------------------------------------------------
# Core decision cases
# ---------------------------------------------------------------------------

def test_tag_valid_no_victim_goes_to_dispense():
    """Tag seen, no victim -> dispense tag.box_count immediately (DISPENSE)."""
    tag = _Tag(valid=True, box_count=3)
    victim = _Victim(detected=False)
    result = decide_dispense(tag, victim)
    assert result is not None
    next_state, box_count = result
    assert next_state == DISPENSE
    assert box_count == 3


def test_victim_only_goes_to_approach():
    """Victim seen, tag not valid -> drive up first (APPROACH_VICTIM), 1 box."""
    tag = _Tag(valid=False)
    victim = _Victim(detected=True)
    result = decide_dispense(tag, victim)
    assert result is not None
    next_state, box_count = result
    assert next_state == APPROACH_VICTIM
    assert box_count == 1


def test_neither_returns_none():
    """Neither tag nor victim -> keep patrolling (None)."""
    result = decide_dispense(_Tag(valid=False), _Victim(detected=False))
    assert result is None


def test_both_valid_tag_wins():
    """Theoretical edge case (shouldn't happen per arena layout): tag takes priority.

    Tag zones (2/3) and victim zones (1/5) are physically separate — both being
    valid simultaneously should be impossible in practice. But verify the code is
    deterministic: tag wins (more specific signal).
    """
    tag = _Tag(valid=True, box_count=2)
    victim = _Victim(detected=True)
    result = decide_dispense(tag, victim)
    assert result is not None
    next_state, box_count = result
    assert next_state == DISPENSE, "tag should win (more specific signal)"
    assert box_count == 2


# ---------------------------------------------------------------------------
# Box count correctness
# ---------------------------------------------------------------------------

def test_tag_box_count_passed_through():
    """Whatever box_count the tag carries, decide_dispense forwards it exactly."""
    for count in [1, 2, 3, 5]:
        tag = _Tag(valid=True, box_count=count)
        _, returned_count = decide_dispense(tag, _Victim())
        assert returned_count == count, f"expected {count}, got {returned_count}"


def test_victim_box_count_always_one():
    """Victim-only sighting always results in exactly 1 box (approach = 1 person)."""
    victim = _Victim(detected=True)
    _, count = decide_dispense(_Tag(valid=False), victim)
    assert count == 1
