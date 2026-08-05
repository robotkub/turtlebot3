"""Where the reference files live, resolved at runtime.

The same nodes now run in two places with different filesystems: on the Pi the
maps folder is ~/turtlebot3_ws/maps, and in the laptop container
docker-compose.yml mounts it at /maps. A hardcoded path can only be right in
one of them.

This bit us for real: mission_params.yaml pinned
"~/turtlebot3_ws/maps/start_pose.yaml", so once mission_manager moved into the
container `~` became /root, neither reference file existed, and both loaders
silently fell back to their placeholder constants. The symptom was a mission
that localized itself to (0.25, 0.25) -- DEFAULT_START -- and drove to
(0.5, 0.5) -- DEFAULT_ZONES[0] -- while the real start_pose.yaml said (0,0,0)
and three real zones sat in mission_zones.yaml. Nothing errored; it just
quietly did the wrong thing.

So: resolve at runtime, and don't pin these paths in a params file.
"""
import os

# Docker convention -- docker-compose.yml mounts ./maps here.
_DOCKER_MAPS = '/maps'
_PI_MAPS = '~/turtlebot3_ws/maps'


def maps_dir():
    """The maps folder for whichever machine this node is running on."""
    if os.path.isdir(_DOCKER_MAPS):
        return _DOCKER_MAPS
    return os.path.expanduser(_PI_MAPS)


def start_pose_path():
    return os.path.join(maps_dir(), 'start_pose.yaml')


def zones_path():
    return os.path.join(maps_dir(), 'mission_zones.yaml')
