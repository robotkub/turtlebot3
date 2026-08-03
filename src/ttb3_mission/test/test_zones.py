"""Unit tests for ttb3_mission.zones.load_zones().

Pure Python -- no ROS needed (zones.py only imports os + yaml).

Run locally:
    pytest src/ttb3_mission/test/test_zones.py -v
"""
import os
import sys

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from ttb3_mission.zones import DEFAULT_ZONES, load_zones  # noqa: E402


def test_loads_real_file(tmp_path):
    f = tmp_path / "mission_zones.yaml"
    f.write_text("zones:\n  - {x: 1.0, y: 2.0, yaw: 0.5}\n  - {x: 3.0, y: 4.0}\n")
    zones = load_zones(str(f))
    assert zones == [(1.0, 2.0, 0.5), (3.0, 4.0, 0.0)]  # yaw defaults to 0.0


def test_missing_file_falls_back_to_default():
    assert load_zones("/nonexistent/path/mission_zones.yaml") == DEFAULT_ZONES


def test_garbled_file_falls_back_to_default(tmp_path):
    f = tmp_path / "mission_zones.yaml"
    f.write_text("not: valid: yaml: [[[")
    assert load_zones(str(f)) == DEFAULT_ZONES


def test_empty_zones_list_falls_back_to_default(tmp_path):
    f = tmp_path / "mission_zones.yaml"
    f.write_text("zones: []\n")
    assert load_zones(str(f)) == DEFAULT_ZONES


def test_missing_x_or_y_falls_back_to_default(tmp_path):
    f = tmp_path / "mission_zones.yaml"
    f.write_text("zones:\n  - {yaw: 0.5}\n")  # no x/y -- malformed zone entry
    assert load_zones(str(f)) == DEFAULT_ZONES


def test_default_zones_match_old_waypoint_placeholders():
    # These four corners used to live as waypoints_x/y/yaw in
    # mission_params.yaml -- keep them as the code-level fallback so
    # behavior doesn't regress on a checkout with no mission_zones.yaml yet.
    assert DEFAULT_ZONES == [
        (0.5, 0.5, 0.0),
        (1.5, 0.5, 1.57),
        (1.5, 1.5, 3.14),
        (0.5, 1.5, -1.57),
    ]
