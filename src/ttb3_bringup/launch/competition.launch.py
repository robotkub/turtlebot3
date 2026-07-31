"""Competition mode (SRS section 7): NO camera streaming to any laptop, no
Foxglove/RViz -- WiFi bandwidth is shared with 6-7 other teams (N3/N4) and the
robot must run fully autonomously (R10). The camera driver itself still runs
(the mission needs live images for R2/R4) -- only the laptop-facing stream is
removed, never the driver.

Never use this one for practice/tuning -- see debug.launch.py.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    with_robot_base = LaunchConfiguration('with_robot_base')
    with_camera = LaunchConfiguration('with_camera')
    use_mock_hardware = LaunchConfiguration('use_mock_hardware')
    camera_device = LaunchConfiguration('camera_device')
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    default_map = os.path.join(
        os.path.expanduser('~'), 'turtlebot3_ws', 'maps', 'arena_v1.yaml')
    default_nav2_params = os.path.join(
        get_package_share_directory('turtlebot3_navigation2'), 'param', 'humble', 'burger.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('with_robot_base', default_value='true'),
        DeclareLaunchArgument('with_camera', default_value='true'),
        DeclareLaunchArgument('use_mock_hardware', default_value='true',
                               description='Flip to false once the real dispenser is wired up'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0'),
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('params_file', default_value=default_nav2_params),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('turtlebot3_bringup'), '/launch/robot.launch.py']),
            condition=IfCondition(with_robot_base),
        ),

        # Camera driver runs (needed for R2/R4) -- just nothing streams it out.
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera_driver',
            output='screen',
            parameters=[{'video_device': camera_device}],
            condition=IfCondition(with_camera),
        ),

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

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('ttb3_perception'), '/launch/perception.launch.py']),
        ),
        Node(
            package='ttb3_dispenser',
            executable='dispenser_controller',
            name='dispenser_controller',
            output='screen',
            parameters=[{'use_mock_hardware': use_mock_hardware}],
        ),
        Node(
            package='ttb3_mission',
            executable='mission_manager',
            name='mission_manager',
            output='screen',
            parameters=[os.path.join(
                get_package_share_directory('ttb3_mission'), 'config', 'mission_params.yaml')],
        ),
        Node(
            package='ttb3_mission',
            executable='button_handler',
            name='button_handler',
            output='screen',
        ),
    ])
