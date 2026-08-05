"""Debug mode (SRS section 7), everything on the Pi: camera stream + Foxglove
Bridge on. Never use this one to actually compete -- see competition.launch.py.

This is now just the two halves composed:
    hardware.launch.py  -- drivers, must be on the Pi
    mission.launch.py   -- Nav2 + perception + mission, runs anywhere

**Prefer splitting them.** The whole stack on one Pi 3/4 saturates it: with
Nav2, apriltag and the mission nodes all running, the Pi kept answering ping
while sshd could no longer complete a banner exchange. Instead run

    on the Pi:      ros2 launch ttb3_bringup hardware.launch.py
    on the laptop:  ./ttb3 mission

which is the same set of nodes, just with the thinking on a machine that has
room for it. Keep using this file when you want a self-contained robot and
don't mind the load (or when nothing else is on the network).

Toggle args exist because the hardware is assembled in stages:
  with_robot_base:=false  -- skip turtlebot3_bringup (no OpenCR plugged in)
  with_camera:=false      -- skip the camera driver (no webcam plugged in)
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
        DeclareLaunchArgument('with_robot_base', default_value='true',
                              description='Launch turtlebot3_bringup (needs OpenCR attached)'),
        DeclareLaunchArgument('with_camera', default_value='true',
                              description='Launch the v4l2 camera driver (needs a USB webcam)'),
        DeclareLaunchArgument('use_mock_hardware', default_value='true',
                              description='Use the mock dispenser backend instead of real GPIO'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0'),
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('params_file', default_value=default_nav2_params),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([pkg_share, '/launch/hardware.launch.py']),
            launch_arguments={
                'with_robot_base': with_robot_base,
                'with_camera': with_camera,
                'with_stream': 'true',
                'use_mock_hardware': use_mock_hardware,
                'camera_device': camera_device,
            }.items(),
        ),

        # remote_camera:=false -- the camera is on this same machine, so
        # perception reads /image_raw directly instead of decompressing the
        # stream we just published.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([pkg_share, '/launch/mission.launch.py']),
            launch_arguments={
                'map': map_yaml,
                'params_file': params_file,
                'visualize': 'true',
                'remote_camera': 'false',
                'with_perception': with_camera,
            }.items(),
        ),
    ])
