"""Step 2 of the mapping workflow (SRS section 10), as a real launch file
instead of a shell script. Runs on the LAPTOP. Does the same job as
2_map_start.sh: starts Cartographer (SLAM, builds the map) + opens RViz2 so
you can watch the map appear live.

Deliberately lives here, NOT inside a colcon package -- per the SRS, it
doesn't need to be built, just launched directly:
    ros2 launch scripts/mapping.launch.py
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('turtlebot3_cartographer'),
                '/launch/cartographer.launch.py']),
        ),
    ])
