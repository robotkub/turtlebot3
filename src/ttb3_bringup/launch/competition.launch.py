"""Competition mode: NO camera streaming to any laptop, no
Foxglove -- WiFi bandwidth is shared with 6-7 other teams and the
robot must run fully autonomously (R10). The camera driver itself still runs
(the mission needs live images) -- only the laptop-facing stream is
removed, never the driver.

Never use this one for practice/tuning -- see debug.launch.py.

Like debug, this is the two halves composed, and everything lands on the Pi:
    hardware.launch.py  -- drivers
    mission.launch.py   -- Nav2 + perception + mission

Running fully on the robot is a deliberate choice HERE, not just habit: R10
wants autonomy with no laptop in the loop, and a laptop that wanders out of
WiFi range mid-run would take the mission's brain with it. If you do decide to
offload compute on competition day, run hardware.launch.py here and
`ros2 launch ttb3_bringup mission.launch.py visualize:=false` on a machine you
trust to stay connected -- but understand you've just made the WiFi link a
single point of failure for the whole run.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def _default_maps_dir():
    if os.path.isdir('/maps'):
        return '/maps'
    return os.path.expanduser('~/turtlebot3_ws/maps')


def generate_launch_description():
    with_robot_base = LaunchConfiguration('with_robot_base')
    with_camera = LaunchConfiguration('with_camera')
    use_mock_hardware = LaunchConfiguration('use_mock_hardware')
    camera_device = LaunchConfiguration('camera_device')
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    pkg_share = get_package_share_directory('ttb3_bringup')
    default_map = os.path.join(_default_maps_dir(), 'arena_v1.yaml')
    default_nav2_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('with_robot_base', default_value='true'),
        DeclareLaunchArgument('with_camera', default_value='true'),
        DeclareLaunchArgument('use_mock_hardware', default_value='true',
                              description='Flip to false once the real dispenser is wired up'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0'),
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('params_file', default_value=default_nav2_params),

        # with_stream:=false is the whole difference from debug: the driver
        # runs, nothing republishes it onto the shared WiFi.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([pkg_share, '/launch/hardware.launch.py']),
            launch_arguments={
                'with_robot_base': with_robot_base,
                'with_camera': with_camera,
                'with_stream': 'false',
                'use_mock_hardware': use_mock_hardware,
                'camera_device': camera_device,
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([pkg_share, '/launch/mission.launch.py']),
            launch_arguments={
                'map': map_yaml,
                'params_file': params_file,
                'visualize': 'false',
                'remote_camera': 'false',
                'with_perception': with_camera,
            }.items(),
        ),
    ])
