"""Navigation only: Nav2 (AMCL localization + planner/controller) against a
saved map, using the team's tunable params file (config/nav2_params.yaml).

Also brings up keyboard teleop + joystick teleop, muxed against Nav2's own
cmd_vel via twist_mux (see config/twist_mux_navigation.yaml) -- Nav2 drives
by default, but grabbing the keyboard or the joystick overrides it
immediately, same priority order as mapping.launch.py (joy > keyboard > nav).

Standalone so you can bring up navigation by itself to test/tune it. The map
path auto-detects Docker vs bare-metal (same as mapping.launch.py) so you
don't need to pass map:=... by hand on the laptop:
    ROS_DOMAIN_ID=42 ROBOT_IP=<pi ip> docker compose run --rm ttb3-compute \\
        ros2 launch ttb3_bringup navigation.launch.py visualize:=true

debug.launch.py and competition.launch.py include this instead of wiring nav2
inline, so the map/params defaults live in one place. They always run
bare-metal on the Pi (never Docker), so they keep their own fixed
~/turtlebot3_ws/maps/arena_v1.yaml default -- only this standalone launch
(used from the laptop, in Docker) needs the auto-detect.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap


def _default_maps_dir():
    # /maps is the Docker convention (docker-compose.yml mounts ./maps
    # there). Bare-metal has no such mount, so fall back to the fixed
    # workspace location. Same helper as mapping.launch.py.
    if os.path.isdir('/maps'):
        return '/maps'
    return os.path.expanduser('~/turtlebot3_ws/maps')


def generate_launch_description():
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    visualize = LaunchConfiguration('visualize')

    default_map = os.path.join(_default_maps_dir(), 'arena_v1.yaml')
    default_params = os.path.join(
        get_package_share_directory('ttb3_bringup'), 'config', 'nav2_params.yaml')
    joy_params = os.path.join(
        get_package_share_directory('ttb3_bringup'), 'config', 'teleop_joy.yaml')
    twist_mux_params = os.path.join(
        get_package_share_directory('ttb3_bringup'), 'config', 'twist_mux_navigation.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map,
                               description='Full path to the saved map yaml (see maps/)'),
        DeclareLaunchArgument('params_file', default_value=default_params,
                               description="The team's tunable Nav2 params (config/nav2_params.yaml)"),
        DeclareLaunchArgument('visualize', default_value='true',
                               description='Launch Foxglove Bridge for web/remote visualization'),

        # GroupAction scopes SetRemap to just this include -- without the
        # group, the remap would leak onto every later action in this list
        # (teleop, joy, twist_mux) since SetRemap otherwise applies to
        # everything visited after it. Nav2's controller_server ends up
        # publishing on cmd_vel_nav instead of cmd_vel, so twist_mux below
        # can arbitrate it against manual teleop/joy input.
        GroupAction([
            SetRemap(src='cmd_vel', dst='cmd_vel_nav'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    get_package_share_directory('nav2_bringup'), '/launch/bringup_launch.py']),
                launch_arguments={
                    'slam': 'False',  # nav2_bringup evals this via PythonExpression -- must be capitalized
                    'map': map_yaml,
                    'params_file': params_file,
                    'use_sim_time': 'false',
                }.items(),
            ),
        ]),

        Node(
            package='turtlebot3_teleop',
            executable='teleop_keyboard',
            name='teleop_keyboard',
            output='screen',
            remappings=[('cmd_vel', 'cmd_vel_teleop')],
        ),

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

        # Arbitrates Nav2 vs. keyboard vs. joy onto the single /cmd_vel the
        # robot actually drives on -- joy beats keyboard beats Nav2 (see
        # config/twist_mux_navigation.yaml), so a manual override always
        # wins over autonomous driving.
        Node(
            package='twist_mux', executable='twist_mux', name='twist_mux',
            output='screen',
            parameters=[twist_mux_params],
            remappings=[('cmd_vel_out', 'cmd_vel')],
        ),

        IncludeLaunchDescription(
            XMLLaunchDescriptionSource([
                get_package_share_directory('foxglove_bridge'), '/launch/foxglove_bridge_launch.xml']),
            condition=IfCondition(visualize),
        ),
    ])
