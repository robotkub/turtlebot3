"""Build a map of the arena (SRS section 10, R1). ONE launch file -- no shell
scripts. The robot must already be up (`ros2 launch turtlebot3_bringup
robot.launch.py` on the Pi).

Starts SLAM (slam_toolbox, online-async) + map_autosaver + joystick teleop,
muxed onto /cmd_vel via twist_mux, so the map is written to disk continuously
and again when you Ctrl-C:
    ROS_DOMAIN_ID=42 ROBOT_IP=<pi ip> docker compose run --rm ttb3-compute \\
        ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true

For keyboard driving, run teleop_keyboard SEPARATELY, in its own terminal --
it needs raw control of a real TTY to read keystrokes, which `ros2 launch`
does not give child processes (confirmed: bundling it here made it crash
with `termios.error: Inappropriate ioctl for device`). Remap its cmd_vel so
twist_mux picks it up:
    docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard \\
        --ros-args -r cmd_vel:=cmd_vel_teleop
Joy still outranks keyboard either way (see config/twist_mux_mapping.yaml).

When the map looks complete, just kill this launch -- the map is already saved.
The map always lands in the maps folder -- no `cd` required, run from anywhere.
That resolves to /maps/arena_v1 in the Docker container (the mounted volume).
Pass an absolute path in `map_path` to override.

Foxglove is the only visualizer used in this project. Watch the map build at
ws://localhost:8765 (see docs/en/08-foxglove.md).

SLAM params live in config/slam_toolbox_mapping.yaml. The map frame origin is
still the robot's pose at launch, exactly as it was under Cartographer, so
maps/start_pose.yaml's (0, 0, 0) START-box convention is unchanged.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
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
    use_sim_time = LaunchConfiguration('use_sim_time')
    maps_dir = _default_maps_dir()
    pkg_share = get_package_share_directory('ttb3_bringup')
    joy_params = os.path.join(pkg_share, 'config', 'teleop_joy.yaml')
    twist_mux_params = os.path.join(pkg_share, 'config', 'twist_mux_mapping.yaml')
    slam_params = os.path.join(pkg_share, 'config', 'slam_toolbox_mapping.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('visualize', default_value='true',
                               description='Launch Foxglove Bridge for web/remote visualization'),
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Use /clock instead of wall time -- set true only when '
                        'mapping from a bag played with --clock'),
        DeclareLaunchArgument(
            'map_path',
            default_value=os.path.join(maps_dir, 'map_autosave'),
            description='Where to save the map (<path>.pgm + .yaml). '
                        'A bare name (e.g. "arena_v1") always resolves against '
                        'the maps folder, regardless of the launch directory.'),

        # Node, not an upstream include: turtlebot3_cartographer shipped a
        # launch file, slam_toolbox expects you to bring your own params, so
        # the tuning is ours and lives in config/slam_toolbox_mapping.yaml.
        # `name` must stay 'slam_toolbox' -- that's the key the params file is
        # written under, and a mismatch silently ignores every value in it.
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[slam_params, {'use_sim_time': use_sim_time}],
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

        # teleop_keyboard is NOT launched here -- run it separately, see the
        # module docstring. ros2 launch doesn't give child processes a real
        # TTY, and teleop_keyboard needs raw terminal control to read
        # keystrokes (crashes with termios.error otherwise).

        # joy_node reads the controller device, teleop_twist_joy
        # turns /joy into cmd_vel_joy per config/teleop_joy.yaml.
        Node(
            package='joy', executable='joy_node', name='joy_node',
            output='screen'
        ),
        Node(
            package='teleop_twist_joy', executable='teleop_node',
            name='teleop_twist_joy_node', output='screen',
            parameters=[joy_params],
            remappings=[('cmd_vel', 'cmd_vel_joy')],
        ),

        # Arbitrates keyboard vs. joy onto the single /cmd_vel the robot
        # actually drives on -- joy has higher priority (see
        # config/twist_mux_mapping.yaml), so grabbing the controller
        # always overrides the keyboard.
        Node(
            package='twist_mux', executable='twist_mux', name='twist_mux',
            output='screen',
            parameters=[twist_mux_params],
            remappings=[('cmd_vel_out', 'cmd_vel')],
        ),
    ])
