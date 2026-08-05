"""Read the mission zone list (maps/mission_zones.yaml).

This file is the single source of truth for which locations the robot visits
during SEARCH -- replaces the old parallel waypoints_x/y/yaw
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


def read_zones(path):
    """Return the zones actually in the file, as (x, y, yaw) tuples, with NO
    fallback -- an empty list means "the file has no zones".

    This is deliberately separate from load_zones(): a writer that built its
    new list from load_zones() would silently bake the four DEFAULT_ZONES
    placeholders into the file the first time anyone saved a real zone."""
    try:
        with open(os.path.expanduser(path)) as f:
            data = yaml.safe_load(f) or {}
        zones = data.get('zones') or []
        return [
            (float(z['x']), float(z['y']), float(z.get('yaw', 0.0)))
            for z in zones
        ]
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        return []


def load_zones(path):
    """Return a list of (x, y, yaw) tuples, in visit order. Falls back to
    DEFAULT_ZONES if the file is missing, unreadable, or has no zones --
    the mission must never crash just because the reference file isn't
    there yet."""
    return read_zones(path) or DEFAULT_ZONES


def save_zones(path, zones):
    """Overwrite the zone file with `zones` (an iterable of (x, y, yaw)), in
    visit order. Creates the parent directory if needed."""
    path = os.path.expanduser(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    rows = [
        {'x': round(float(x), 4), 'y': round(float(y), 4),
         'yaw': round(float(yaw), 4)}
        for x, y, yaw in zones
    ]
    with open(path, 'w') as f:
        f.write(
            '# Mission zones, in visit order (written by /save_zone -- see\n'
            '# zone_recorder.py). Hand-editing is fine; mission_manager reads\n'
            '# this file when it starts, so restart it to pick up changes.\n')
        yaml.safe_dump({'zones': rows}, f,
                       default_flow_style=None, sort_keys=True)


def append_zone(path, x, y, yaw):
    """Append one zone to the file and return the full list after appending."""
    zones = read_zones(path)
    zones.append((float(x), float(y), float(yaw)))
    save_zones(path, zones)
    return zones
