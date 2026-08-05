"""Debug mode (SRS section 7): camera stream + Foxglove Bridge on, LAN/Ethernet
assumed. Never use this one to actually compete -- see competition.launch.py.

Toggle args exist mainly because no OpenCR/camera is attached to this Pi yet:
  with_robot_base:=false  -- skip turtlebot3_bringup (no OpenCR plugged in)
  with_camera:=false      -- skip the camera driver (no webcam plugged in)
so the mission nodes + Nav2 + Foxglove can still be smoke-tested today.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource
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
        get_package_share_directory('ttb3_bringup'), 'config', 'nav2_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('with_robot_base', default_value='true',
                               description='Launch turtlebot3_bringup (needs OpenCR attached)'),
        DeclareLaunchArgument('with_camera', default_value='true',
                               description='Launch the v4l2 camera driver (needs USB webcam attached)'),
        DeclareLaunchArgument('use_mock_hardware', default_value='true',
                               description='Use the mock dispenser backend instead of real GPIO'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0'),
        DeclareLaunchArgument('map', default_value=default_map,
                               description='Full path to the saved map yaml (see turtlebot3_ws/maps/)'),
        DeclareLaunchArgument('params_file', default_value=default_nav2_params),

        # --- Layer 1/2/3: robot base (OpenCR bridge via turtlebot3_node) ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('turtlebot3_bringup'), '/launch/robot.launch.py']),
            condition=IfCondition(with_robot_base),
        ),

        # --- camera + compressed stream for the debug laptop (N3: compressed only) ---
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera_driver',
            output='screen',
            parameters=[{'video_device': camera_device}],
            condition=IfCondition(with_camera),
        ),
        Node(
            package='image_transport',
            executable='republish',
            name='camera_compressed_republish',
            arguments=['raw', 'compressed'],
            remappings=[('in', '/image_raw'), ('out/compressed', '/image_raw/compressed')],
            condition=IfCondition(with_camera),
        ),

        # --- Layer 4: Nav2 (AMCL + planner/controller against the saved map) ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('ttb3_bringup'), '/launch/navigation.launch.py']),
            # visualize:=false is load-bearing. navigation.launch.py starts a
            # foxglove_bridge of its own by default, and this file starts one
            # below -- two nodes both named foxglove_bridge on port 8765.
            # They don't merely collide on the port: both died on startup with
            # "parameter 'port' has invalid type ... {integer} ... {string}",
            # so debug.launch.py came up with NO bridge at all and Foxglove
            # just reported "connection failed".
            launch_arguments={
                'map': map_yaml,
                'params_file': params_file,
                'visualize': 'false',
            }.items(),
        ),

        # --- Layer 5: our mission nodes ---
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
            executable='zone_recorder',
            name='zone_recorder',
            output='screen',
        ),
        Node(
            package='ttb3_mission',
            executable='button_handler',
            name='button_handler',
            output='screen',
        ),

        # --- debug-only visualization (SRS section 7) ---
        IncludeLaunchDescription(
            XMLLaunchDescriptionSource([
                get_package_share_directory('foxglove_bridge'), '/launch/foxglove_bridge_launch.xml']),
        ),
    ])
