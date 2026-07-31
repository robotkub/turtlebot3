"""Bundles apriltag_ros's detector node + our apriltag_detector/victim_detector
wrappers, so ttb3_bringup's debug/competition launch files can include this one
file instead of wiring up three nodes by hand."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('ttb3_perception')

    camera_image_topic = LaunchConfiguration('camera_image_topic')

    return LaunchDescription([
        DeclareLaunchArgument(
            'camera_image_topic', default_value='/image_raw',
            description='Raw camera image topic feeding both AprilTag and victim detection'),

        Node(
            package='apriltag_ros',
            executable='apriltag_node',
            name='apriltag_node',
            output='screen',
            parameters=[os.path.join(pkg_share, 'config', 'tags_36h11.yaml')],
            remappings=[
                ('image_rect', camera_image_topic),
                ('detections', '/apriltag/detections'),
            ],
        ),
        Node(
            package='ttb3_perception',
            executable='apriltag_detector',
            name='apriltag_detector',
            output='screen',
        ),
        Node(
            package='ttb3_perception',
            executable='victim_detector',
            name='victim_detector',
            output='screen',
            parameters=[
                os.path.join(pkg_share, 'config', 'victim_detector.yaml'),
                {'image_topic': camera_image_topic},
            ],
        ),
    ])
