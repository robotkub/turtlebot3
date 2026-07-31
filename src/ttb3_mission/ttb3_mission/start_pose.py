"""Read/write the START pose reference file (maps/start_pose.yaml).

This file is the single source of truth for where the robot starts and returns
to. mission_manager re-reads it on every use so a save takes effect live,
and the save_start_pose service writes it. Kept dependency-light (pyyaml is
already pulled in by ROS) and tolerant of a missing/garbled file -- a bad read
falls back to the default rather than crashing the mission node."""
import os

import yaml

DEFAULT_START = (0.25, 0.25, 0.0)


def load_start_pose(path):
    """Return (x, y, yaw). Falls back to DEFAULT_START if the file is missing
    or unreadable -- the mission must never crash just because the reference
    file isn't there yet."""
    try:
        with open(os.path.expanduser(path)) as f:
            data = yaml.safe_load(f) or {}
        return (
            float(data.get('x', DEFAULT_START[0])),
            float(data.get('y', DEFAULT_START[1])),
            float(data.get('yaw', DEFAULT_START[2])),
        )
    except (OSError, ValueError, yaml.YAMLError):
        return DEFAULT_START


def save_start_pose(path, x, y, yaw):
    """Overwrite the reference file with a new START pose. Creates the parent
    directory if needed."""
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(
            '# START pose reference (written by /save_start_pose). '
            'See maps/start_pose.yaml header for how this file is used.\n')
        yaml.safe_dump({'x': float(x), 'y': float(y), 'yaw': float(yaw)}, f,
                       default_flow_style=False, sort_keys=True)
