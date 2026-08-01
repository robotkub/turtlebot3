"""Build a map of the arena (SRS section 10, R1). ONE launch file -- no shell
scripts. The robot must already be up (`ros2 launch turtlebot3_bringup
robot.launch.py` on the Pi).

Starts SLAM (Cartographer) + map_autosaver so the map is written to disk
continuously and again when you Ctrl-C. Drive around with:
    docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard
When the map looks complete, just kill this launch -- the map is already saved.

The map always lands in the maps folder -- no `cd` required, run from anywhere:
    ROS_DOMAIN_ID=42 ROBOT_IP=<pi ip> docker compose run --rm ttb3-compute \\
        ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true

That resolves to /maps/arena_v1 in the Docker container (the mounted volume).
Pass an absolute path in `map_path` to override.

Foxglove is the only visualizer used in this project. Watch the map build at
ws://localhost:8765 (see docs/en/08-foxglove.md).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def _default_maps_dir():
    # /maps is the Docker convention (docker-compose.yml mounts ./maps
    # there and sets it as the working dir). Bare-metal has no such mount,
    # so fall back to the fixed workspace location -- either way, this
    # doesn't depend on the directory the launch happened to start from.
    if os.path.isdir('/maps'):
        return '/maps'
    return os.path.expanduser('~/turtlebot3_ws/maps')


def generate_launch_description():
    map_path = LaunchConfiguration('map_path')
    visualize = LaunchConfiguration('visualize')
    maps_dir = _default_maps_dir()

    return LaunchDescription([
        DeclareLaunchArgument('visualize', default_value='true',
                               description='Launch Foxglove Bridge for web/remote visualization'),
        DeclareLaunchArgument(
            'map_path',
            default_value=os.path.join(maps_dir, 'map_autosave'),
            description='Where to save the map (<path>.pgm + .yaml). '
                        'A bare name (e.g. "arena_v1") always resolves against '
                        'the maps folder, regardless of the launch directory.'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('turtlebot3_cartographer'),
                '/launch/cartographer.launch.py']),
            # Foxglove is the only visualizer this project uses; this suppresses
            # the upstream cartographer launch's own default GUI window.
            launch_arguments={'use_sim_time': 'false', 'use_rviz': 'false'}.items(),
        ),

        Node(
            package='ttb3_bringup',
            executable='map_autosaver',
            name='map_autosaver',
            output='screen',
            parameters=[{
                'map_path': PythonExpression(
                    ["'", map_path, "' if '", map_path,
                     "'.startswith('/') or '", map_path, "'.startswith('~') "
                     "else '", maps_dir, "' + '/' + '", map_path, "'"]),
            }],
        ),

        IncludeLaunchDescription(
            XMLLaunchDescriptionSource([
                get_package_share_directory('foxglove_bridge'), '/launch/foxglove_bridge_launch.xml']),
            condition=IfCondition(visualize),
        ),
    ])
