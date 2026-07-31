"""Navigation only: Nav2 (AMCL localization + planner/controller) against a
saved map, using the team's tunable params file (config/nav2_params.yaml).

Standalone so you can bring up navigation by itself to test/tune it:
    ros2 launch ttb3_bringup navigation.launch.py map:=~/turtlebot3_ws/maps/arena_v1.yaml

debug.launch.py and competition.launch.py include this instead of wiring nav2
inline, so the map/params defaults live in one place.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    default_map = os.path.join(
        os.path.expanduser('~'), 'turtlebot3_ws', 'maps', 'arena_v1.yaml')
    default_params = os.path.join(
        get_package_share_directory('ttb3_bringup'), 'config', 'nav2_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map,
                               description='Full path to the saved map yaml (see maps/)'),
        DeclareLaunchArgument('params_file', default_value=default_params,
                               description="The team's tunable Nav2 params (config/nav2_params.yaml)"),

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
    ])
