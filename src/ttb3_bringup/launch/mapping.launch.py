"""Build a map of the arena (SRS section 10, R1). ONE launch file -- no shell
scripts. The robot must already be up (`ros2 launch turtlebot3_bringup
robot.launch.py` on the Pi).

Starts SLAM (Cartographer) + map_autosaver + teleop (keyboard by default) so
the map is written to disk continuously and again when you Ctrl-C, and you
can drive right away without a second terminal:
    ROS_DOMAIN_ID=42 ROBOT_IP=<pi ip> docker compose run --rm ttb3-compute \\
        ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true

teleop:=keyboard (default) -- drive with the keyboard, same as running
    ros2 run turtlebot3_teleop teleop_keyboard
    by hand, just bundled in. Needs the container's tty (docker-compose.yml
    already sets stdin_open/tty for this).
teleop:=joy -- drive with a gamepad instead (joy_node + teleop_twist_joy,
    config/teleop_joy.yaml). Requires a controller reachable inside the
    container -- docker-compose.yml passes through /dev/input, but Docker
    Desktop (Mac/Windows) does NOT support this passthrough, only Linux
    hosts. On Mac/Windows, stick with teleop:=keyboard.
teleop:=none -- no teleop node at all, drive from a separate terminal
    yourself (the old way).

When the map looks complete, just kill this launch -- the map is already saved.
The map always lands in the maps folder -- no `cd` required, run from anywhere.
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
    teleop = LaunchConfiguration('teleop')
    maps_dir = _default_maps_dir()
    joy_params = os.path.join(
        get_package_share_directory('ttb3_bringup'), 'config', 'teleop_joy.yaml')

    is_keyboard = IfCondition(PythonExpression(["'", teleop, "' == 'keyboard'"]))
    is_joy = IfCondition(PythonExpression(["'", teleop, "' == 'joy'"]))

    return LaunchDescription([
        DeclareLaunchArgument('visualize', default_value='true',
                               description='Launch Foxglove Bridge for web/remote visualization'),
        DeclareLaunchArgument(
            'teleop', default_value='keyboard',
            description='Which teleop to bring up while mapping: '
                        'keyboard (default) | joy (gamepad, Linux hosts only) | none'),
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

        # teleop:=keyboard -- reads raw keystrokes from the container's tty
        # (docker-compose.yml sets stdin_open/tty so `docker compose run`
        # attaches your terminal to it directly, no separate window needed).
        Node(
            package='turtlebot3_teleop',
            executable='teleop_keyboard',
            name='teleop_keyboard',
            output='screen',
            condition=is_keyboard,
        ),

        # teleop:=joy -- joy_node reads the controller device, teleop_twist_joy
        # turns /joy into /cmd_vel per config/teleop_joy.yaml.
        Node(
            package='joy', executable='joy_node', name='joy_node',
            output='screen', condition=is_joy,
        ),
        Node(
            package='teleop_twist_joy', executable='teleop_node',
            name='teleop_twist_joy_node', output='screen',
            parameters=[joy_params], condition=is_joy,
        ),
    ])
