"""Build a map of the arena (SRS section 10, R1). ONE launch file -- no shell
scripts. Runs on the LAPTOP; the robot must already be up
(`ros2 launch turtlebot3_bringup robot.launch.py` on the Pi).

Starts SLAM (Cartographer) + RViz to watch the map grow, plus map_autosaver so
the map is written to disk continuously and again when you Ctrl-C. Drive around
with `ros2 run turtlebot3_teleop teleop_keyboard`; when the map looks complete,
just kill this launch -- the map is already saved.

The map is saved to `map_path` (default: <current directory>/map_autosave),
so `cd` to where you want it (e.g. ~/turtlebot3_ws/maps) before launching:
    cd ~/turtlebot3_ws/maps
    ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1
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


def generate_launch_description():
    use_rviz = LaunchConfiguration('use_rviz')
    map_path = LaunchConfiguration('map_path')
    visualize = LaunchConfiguration('visualize')
    # Resolve a bare name against the directory the launch was started from, so
    # `map_path:=arena_v1` lands in the folder you cd'd to.
    launch_cwd = os.getcwd()

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='true',
                               description='Open RViz to watch the map build'),
        DeclareLaunchArgument('visualize', default_value='true',
                               description='Launch Foxglove Bridge for web/remote visualization'),
        DeclareLaunchArgument(
            'map_path',
            default_value=os.path.join(launch_cwd, 'map_autosave'),
            description='Where to save the map (<path>.pgm + .yaml). '
                        'Relative names resolve against the launch directory.'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('turtlebot3_cartographer'),
                '/launch/cartographer.launch.py']),
            launch_arguments={'use_sim_time': 'false', 'use_rviz': use_rviz}.items(),
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
                     "else '", launch_cwd, "' + '/' + '", map_path, "'"]),
            }],
        ),

        IncludeLaunchDescription(
            XMLLaunchDescriptionSource([
                get_package_share_directory('foxglove_bridge'), '/launch/foxglove_bridge_launch.xml']),
            condition=IfCondition(visualize),
        ),
    ])
