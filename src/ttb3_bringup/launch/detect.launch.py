"""Perception only -- apriltag + victim detection, with no Nav2 and no mission.

For answering one question fast: is the camera pipeline actually detecting,
and how many boxes does the tag mean? apriltag_detector prints that directly:

    TAG 3  ->  3 boxes
    no tag in view

Bringing up the whole mission stack to test a tag takes ~40s, floods the log,
and drags in localisation problems that have nothing to do with the camera.
This starts three nodes, and by default nothing else -- foxglove_bridge is
opt-in via visualize:=true because its logging drowns the line above.

The robot still needs `ttb3-hardware.service` running (that is what publishes
the camera); this half just consumes it. Nothing here commands the base, so
the robot cannot move while this is up.

remote_camera defaults to true -- same reasoning as mission.launch.py: the
off-robot case is the one people get wrong. Set it false when running on the
Pi itself, where /image_raw is already local and decoding JPEG is wasted work.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def generate_launch_description():
    visualize = LaunchConfiguration('visualize')
    remote_camera = LaunchConfiguration('remote_camera')
    camera_image_topic = LaunchConfiguration('camera_image_topic')

    return LaunchDescription([
        DeclareLaunchArgument(
            'visualize', default_value='false',
            description='Run foxglove_bridge on 8765 to watch the camera. OFF '
                        'by default: the bridge logs a line per topic per '
                        'connection-graph tick, which buries the one line you '
                        'started this command to read. Turn it on when you '
                        'need to see WHERE the tag is, not just whether it '
                        'was read'),
        DeclareLaunchArgument(
            'remote_camera', default_value='true',
            description='true when this runs off-robot: frames arrive '
                        'compressed and both detectors decode JPEG themselves'),
        DeclareLaunchArgument(
            'camera_image_topic', default_value='/image_raw',
            description='BASE camera topic (no /compressed suffix -- the '
                        'transport argument adds it)'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('ttb3_perception'),
                '/launch/perception.launch.py']),
            launch_arguments={
                'camera_image_topic': camera_image_topic,
                'image_transport': PythonExpression([
                    "'compressed' if '", remote_camera, "' == 'true' else 'raw'"]),
            }.items(),
        ),

        # No GroupAction needed here (unlike mission.launch.py): perception
        # .launch.py declares no `visualize` of its own, so nothing can leak
        # into this scope and switch the bridge off behind our backs.
        IncludeLaunchDescription(
            XMLLaunchDescriptionSource([
                get_package_share_directory('foxglove_bridge'),
                '/launch/foxglove_bridge_launch.xml']),
            condition=IfCondition(visualize),
        ),
    ])
