"""The robot half: everything that must run ON the Pi because it is wired to
physical hardware. Sensors, motors, camera, dispenser servo -- and nothing
that merely thinks.

Pair it with mission.launch.py, which is the thinking half and can run either
on this Pi or on a laptop (see `./ttb3 mission`). Splitting them is the point:
the full stack on one Pi 3/4 saturates it -- Nav2 plus apriltag plus the
mission nodes left sshd unable to complete a banner exchange while the machine
still answered ping.

    on the Pi:      ros2 launch ttb3_bringup hardware.launch.py
    on the laptop:  ./ttb3 mission

debug.launch.py and competition.launch.py include this file plus
mission.launch.py, so running everything on the Pi still works unchanged.

Toggles exist because the hardware is assembled in stages:
  with_robot_base:=false  -- no OpenCR plugged in
  with_camera:=false      -- no USB webcam plugged in (there is no /dev/video0)
  with_stream:=false      -- run the camera but don't publish the compressed
                             stream (competition: the mission needs images,
                             the laptop does not, and WiFi is shared)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    with_robot_base = LaunchConfiguration('with_robot_base')
    with_camera = LaunchConfiguration('with_camera')
    with_stream = LaunchConfiguration('with_stream')
    with_dispenser = LaunchConfiguration('with_dispenser')
    use_mock_hardware = LaunchConfiguration('use_mock_hardware')
    camera_device = LaunchConfiguration('camera_device')

    return LaunchDescription([
        DeclareLaunchArgument('with_robot_base', default_value='true',
                              description='Launch turtlebot3_bringup (needs OpenCR attached)'),
        DeclareLaunchArgument('with_camera', default_value='true',
                              description='Launch the v4l2 camera driver (needs a USB webcam)'),
        DeclareLaunchArgument('with_stream', default_value='true',
                              description='Publish /image_raw/compressed for a remote laptop'),
        DeclareLaunchArgument('with_dispenser', default_value='true',
                              description='Run dispenser_controller here (it drives the GPIO servo)'),
        DeclareLaunchArgument('use_mock_hardware', default_value='true',
                              description='Flip to false once the real dispenser servo is wired up'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0'),

        # Base: OpenCR bridge (motors, IMU, buttons) + LDS lidar.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('turtlebot3_bringup'), '/launch/robot.launch.py']),
            condition=IfCondition(with_robot_base),
        ),

        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera_driver',
            output='screen',
            parameters=[{
                'video_device': camera_device,
                # This camera (Jieli 5258:4a55) only offers MJPG -- no YUYV,
                # which is what v4l2_camera would otherwise ask for.
                'pixel_format': 'MJPG',
                'image_size': [640, 480],
                # Every control below is pinned because the camera's firmware
                # reports DEFAULTS OUTSIDE ITS OWN ADVERTISED RANGE:
                #   brightness  min=-127 max=127  default=-8193
                #   contrast    min=0    max=511  default=57343
                #   gamma       min=10   max=30   default=61432
                # (-8193 and 57343 are both 0xDFFF, i.e. uninitialised.)
                # v4l2_camera declares each control as a ROS parameter using
                # that default, the value fails its own range check, and the
                # node dies at startup with "parameter 'brightness' could not
                # be set: doesn't comply with integer range". Pinning valid
                # values means the driver never reads the broken defaults.
                'brightness': 0,
                'contrast': 0,
                'saturation': 0,
                'gamma': 10,
                'gain': 4,
                'white_balance_temperature': 4500,
                'sharpness': 0,
                'backlight_compensation': 0,
            }],
            condition=IfCondition(with_camera),
        ),
        # Compressed is the only thing that should ever cross the WiFi.
        # mission.launch.py decompresses it back on the far side when it runs
        # off-robot; running on the Pi it just reads /image_raw directly.
        #
        # Gated on with_camera as well as with_stream: with no camera there is
        # no /image_raw to republish, and starting it anyway leaves a node
        # sitting on a topic that will never exist.
        Node(
            package='image_transport',
            executable='republish',
            name='camera_compressed_republish',
            arguments=['raw', 'compressed'],
            remappings=[('in', '/image_raw'), ('out/compressed', '/image_raw/compressed')],
            condition=IfCondition(PythonExpression([
                "'", with_camera, "' == 'true' and '", with_stream, "' == 'true'"])),
        ),

        # Stays robot-side even when the mission thinks on a laptop: it drives
        # a servo on this Pi's GPIO. It's topic-driven (/dispense_command),
        # so the mission can command it from anywhere.
        Node(
            package='ttb3_dispenser',
            executable='dispenser_controller',
            name='dispenser_controller',
            output='screen',
            parameters=[{'use_mock_hardware': use_mock_hardware}],
            condition=IfCondition(with_dispenser),
        ),
    ])
