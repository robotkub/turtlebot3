"""Read the mission zone list (maps/mission_zones.yaml).

This file is the single source of truth for which locations the robot visits
during SEARCH (R1/R2/R4) -- replaces the old parallel waypoints_x/y/yaw
ROS params. mission_manager visits each zone in order: drive there, check for
a tag/victim (see decide_dispense() in mission_manager.py), dispense if found,
then move on to the next zone regardless -- RETURN_HOME only once every zone
on the list has been visited.

Kept dependency-light (pyyaml is already pulled in by ROS) and tolerant of a
missing/garbled file -- a bad read falls back to DEFAULT_ZONES rather than
crashing the mission node, same policy as start_pose.py."""
import os

import yaml

# Same four placeholder corners the old waypoints_x/y/yaw params used --
# kept as the fallback so behavior doesn't regress if mission_zones.yaml
# is missing (e.g. brand new checkout, before a real map/zones exist).
DEFAULT_ZONES = [
    (0.5, 0.5, 0.0),
    (1.5, 0.5, 1.57),
    (1.5, 1.5, 3.14),
    (0.5, 1.5, -1.57),
]


def load_zones(path):
    """Return a list of (x, y, yaw) tuples, in visit order. Falls back to
    DEFAULT_ZONES if the file is missing, unreadable, or has no zones --
    the mission must never crash just because the reference file isn't
    there yet."""
    try:
        with open(os.path.expanduser(path)) as f:
            data = yaml.safe_load(f) or {}
        zones = data.get('zones') or []
        parsed = [
            (float(z['x']), float(z['y']), float(z.get('yaw', 0.0)))
            for z in zones
        ]
        return parsed or DEFAULT_ZONES
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        return DEFAULT_ZONES
