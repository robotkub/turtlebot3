"""Bundles apriltag_ros's detector node + our apriltag_detector/victim_detector
wrappers, so ttb3_bringup's debug/competition launch files can include this one
file instead of wiring up three nodes by hand."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('ttb3_perception')

    camera_image_topic = LaunchConfiguration('camera_image_topic')
    image_transport = LaunchConfiguration('image_transport')

    return LaunchDescription([
        DeclareLaunchArgument(
            'camera_image_topic', default_value='/image_raw',
            description='BASE camera image topic feeding AprilTag and victim detection'),
        DeclareLaunchArgument(
            'image_transport', default_value='raw',
            description="'compressed' when the camera is on another machine -- "
                        'both detectors then decode JPEG themselves, which is '
                        'cheaper than republishing to raw in between'),

        Node(
            package='apriltag_ros',
            executable='apriltag_node',
            name='apriltag_node',
            output='screen',
            parameters=[os.path.join(pkg_share, 'config', 'tags_36h11.yaml'),
                        {'image_transport': image_transport}],
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
                # victim_detector picks its message type off the topic name:
                # a name ending in /compressed means CompressedImage.
                {'image_topic': PythonExpression([
                    "'", camera_image_topic, "' + ('/compressed' if '",
                    image_transport, "' == 'compressed' else '')"])},
            ],
        ),
    ])
