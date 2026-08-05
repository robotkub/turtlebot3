"""The thinking half: Nav2, perception, and the mission state machine. No
hardware drivers, so this runs equally well on the Pi or on a laptop.

    on a laptop:  ./ttb3 mission          (Docker, the normal way)
    on the Pi:    ros2 launch ttb3_bringup mission.launch.py

Pair it with hardware.launch.py on the Pi. The whole reason for the split is
load: Nav2 + apriltag + the mission nodes together saturate a Pi 3/4 -- it
kept answering ping while sshd could no longer complete a banner exchange.
Zenoh carries the graph between the two machines, so neither half cares where
the other runs.

Camera topic, and why remote_camera exists: apriltag and the victim detector
want a raw sensor_msgs/Image. On the robot that's just /image_raw. Off the
robot, shipping raw frames over shared WiFi is exactly what the competition
network cannot take, so hardware.launch.py publishes /image_raw/compressed and
BOTH detectors decode the JPEG themselves -- apriltag_node via its
image_transport parameter, victim_detector with cv_bridge.

There is deliberately no republisher in between. `image_transport republish
compressed raw` was tried first and silently produced nothing: it received
/image_raw/compressed at the full 29 Hz, logged no error at all, and never
emitted a single frame on its output topic. Having each consumer decode is
also one less copy of a 640x480 image per frame.

remote_camera defaults to true because the off-robot case is the one people
get wrong; set it false on the Pi, where /image_raw is already local.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, GroupAction, IncludeLaunchDescription)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def _default_maps_dir():
    # /maps is the Docker convention (docker-compose.yml mounts ./maps there);
    # bare-metal on the Pi has no such mount. Same helper the other launch
    # files use.
    if os.path.isdir('/maps'):
        return '/maps'
    return os.path.expanduser('~/turtlebot3_ws/maps')


def generate_launch_description():
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    visualize = LaunchConfiguration('visualize')
    remote_camera = LaunchConfiguration('remote_camera')
    with_perception = LaunchConfiguration('with_perception')

    default_map = os.path.join(_default_maps_dir(), 'arena_v1.yaml')
    default_nav2_params = os.path.join(
        get_package_share_directory('ttb3_bringup'), 'config', 'nav2_params.yaml')


    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('params_file', default_value=default_nav2_params),
        DeclareLaunchArgument(
            'visualize', default_value='true',
            description='Launch Foxglove Bridge. false for competition runs.'),
        DeclareLaunchArgument(
            'remote_camera', default_value='true',
            description='Decompress /image_raw/compressed locally. Set false '
                        'when running on the Pi, where /image_raw is local.'),
        DeclareLaunchArgument(
            'with_perception', default_value='true',
            description='Run apriltag + victim detection (needs a camera feed)'),

        # Nav2. visualize:=false because this file owns the bridge below --
        # two foxglove_bridge nodes on port 8765 kill each other at startup.
        #
        # GroupAction is load-bearing, not decoration. launch_arguments on a
        # bare IncludeLaunchDescription leak into the PARENT scope, so the
        # 'visualize': 'false' below overwrote this file's own `visualize`
        # before the Foxglove include at the bottom evaluated its condition --
        # the bridge silently never started and Foxglove reported nothing but
        # "connection failed". GroupAction is scoped by default and contains
        # it. (navigation.launch.py wraps its own SetRemap for the same
        # reason.)
        GroupAction([
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    get_package_share_directory('ttb3_bringup'),
                    '/launch/navigation.launch.py']),
                launch_arguments={
                    'map': map_yaml,
                    'params_file': params_file,
                    'visualize': 'false',
                }.items(),
            ),
        ]),


        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('ttb3_perception'), '/launch/perception.launch.py']),
            launch_arguments={
                'camera_image_topic': '/image_raw',
                'image_transport': PythonExpression([
                    "'compressed' if '", remote_camera, "' == 'true' else 'raw'"]),
            }.items(),
            condition=IfCondition(with_perception),
        ),

        Node(
            package='ttb3_mission',
            executable='mission_manager',
            name='mission_manager',
            output='screen',
            parameters=[os.path.join(
                get_package_share_directory('ttb3_mission'), 'config', 'mission_params.yaml')],
        ),
        # zone_recorder is NOT started here -- navigation.launch.py, included
        # above, already starts it. Declaring it in both gave two identical
        # /zone_recorder nodes writing the same mission_zones.yaml.
        #
        # Reads SW1/SW2 off /sensor_state, which the OpenCR publishes over the
        # shared graph -- so the physical buttons still start/e-stop the run
        # even with the mission thinking on a laptop.
        Node(
            package='ttb3_mission',
            executable='button_handler',
            name='button_handler',
            output='screen',
        ),

        IncludeLaunchDescription(
            XMLLaunchDescriptionSource([
                get_package_share_directory('foxglove_bridge'),
                '/launch/foxglove_bridge_launch.xml']),
            condition=IfCondition(visualize),
        ),
    ])
