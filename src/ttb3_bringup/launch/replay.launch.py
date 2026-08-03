"""Replay a recorded bag through the full navigation stack -- ONE command,
no robot sensors needed.

    ./ttb3 replay                 # newest bag in ./bags/
    ./ttb3 replay bags/<name>

Starts `ros2 bag play --clock --loop` AND navigation.launch.py (Nav2 + AMCL
+ Foxglove Bridge) together, so you get a complete, driveable-looking system
off recorded data. Watch it at ws://localhost:8765 exactly like a live run.

The Pi still has to be powered ON -- its zenoh router is what all the ROS
traffic flows through -- but nothing needs to be plugged into it: the bag
supplies /scan, /odom and /tf in place of the lidar and OpenCR.

Two details this file exists to get right:

  use_sim_time -- a bag's header stamps are from whenever it was recorded,
  so under wall time tf2 discards every message as hopelessly stale and
  nothing ever localizes. --clock publishes the bag's own timeline and
  use_sim_time:=true puts every node on it.

  ordering -- nav2 nodes that use sim time block until /clock appears, so
  bag playback starts first and nav follows a few seconds later. Without
  the delay the stack can come up against a clock that reads 0.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    bag = LaunchConfiguration('bag')
    rate = LaunchConfiguration('rate')
    map_yaml = LaunchConfiguration('map')

    default_map = os.path.join(
        '/maps' if os.path.isdir('/maps') else os.path.expanduser('~/turtlebot3_ws/maps'),
        'arena_v1.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'bag',
            description='Path to the bag directory (inside the container, '
                        'e.g. /bags/bringup_20260804)'),
        DeclareLaunchArgument(
            'rate', default_value='1.0',
            description='Playback speed multiplier'),
        DeclareLaunchArgument(
            'map', default_value=default_map,
            description='Map to localize against -- should be the one built '
                        'from this same arena, or AMCL has nothing to match'),

        ExecuteProcess(
            cmd=['ros2', 'bag', 'play', bag,
                 '--clock', '--loop', '--rate', rate],
            output='screen',
        ),

        # Let /clock get flowing before nav2 comes up (see module docstring).
        TimerAction(
            period=4.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource([
                        get_package_share_directory('ttb3_bringup'),
                        '/launch/navigation.launch.py']),
                    launch_arguments={
                        'use_sim_time': 'true',
                        'visualize': 'true',
                        'map': map_yaml,
                    }.items(),
                ),
            ],
        ),
    ])
