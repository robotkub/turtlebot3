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
    with_web_stream = LaunchConfiguration('with_web_stream')
    use_mock_hardware = LaunchConfiguration('use_mock_hardware')
    camera_device = LaunchConfiguration('camera_device')
    web_stream_port = LaunchConfiguration('web_stream_port')

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
        DeclareLaunchArgument('with_web_stream', default_value='true',
                              description='Serve /image_raw/compressed as a plain '
                                          'web page (http://skuba.local:8080/) -- '
                                          'no Foxglove or laptop Docker stack needed'),
        DeclareLaunchArgument('web_stream_port', default_value='8080'),

        # Base: OpenCR bridge (motors, IMU, buttons) + LDS lidar.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('turtlebot3_bringup'), '/launch/robot.launch.py']),
            condition=IfCondition(with_robot_base),
        ),

        # usb_cam, not v4l2_camera. This camera offers exactly one format,
        # MJPG (`v4l2-ctl --list-formats` shows a single entry), and
        # v4l2_camera cannot decode it -- it logs "Current pixel format is not
        # supported yet: MJPG", hands cv_bridge an empty encoding and dies with
        # "Unrecognized image encoding []". usb_cam's mjpeg2rgb decodes it.
        #
        # The control values below are pinned because this camera's firmware
        # reports defaults outside its own advertised ranges (brightness
        # min=-127 max=127 default=-8193; contrast min=0 max=511
        # default=57343 -- both 0xDFFF, i.e. uninitialised). A driver that
        # trusts those defaults refuses to start.
        Node(
            package='usb_cam',
            executable='usb_cam_node_exe',
            name='camera_driver',
            output='screen',
            parameters=[{
                'video_device': camera_device,
                'pixel_format': 'mjpeg2rgb',
                # 320x240 @ 4fps, not 640x480 @ 15fps. This is a snapshot
                # cadence on purpose: the mission only reads a tag while the
                # robot is STOPPED sweeping at a zone, so 15fps of live video
                # bought nothing and cost everything.
                #
                # 640x480 MJPEG @15fps is ~4-7 Mbit/s, roughly 97% of all ROS
                # traffic on the WiFi link. It starved /scan so badly that
                # scans arrived up to 50s stale and the costmaps ran on
                # rubbish. apriltag_node's own counters showed 1-17 frames
                # arriving per 10s out of 150 sent -- 89-99% loss.
                #
                # Detection quality is UNCHANGED: tags_36h11.yaml already set
                # detector.decimate: 2.0, so apriltag was halving 640x480 to
                # 320x240 before looking at it anyway. We were paying 4x the
                # bandwidth to ship pixels that got thrown away on arrival.
                # decimate drops to 1.0 to match.
                # BACK to 640x480, but keeping 4fps. Dropping to 320x240 was a
                # mistake: the claim that detection quality would be unchanged
                # (because detector.decimate was already 2.0) was wrong.
                # quad_decimate only downsamples for QUAD DETECTION -- with
                # refine: True the decode and edge-refine steps run on the
                # FULL-resolution image. So 640x480 + decimate 2.0 genuinely
                # reads tags further away than a native 320x240 frame can, and
                # cutting the sensor resolution cut real detection range.
                #
                # The framerate cut is what actually mattered for bandwidth,
                # and it stays. Against the original (640x480 @15fps, published
                # twice because of the duplicate republisher) this is still
                # ~7.5x less traffic, which is plenty of headroom on 2.4 GHz.
                'image_width': 640,
                'image_height': 480,
                'framerate': 4.0,
                'camera_name': 'camera',
                'brightness': 0,
                'contrast': 0,
                'saturation': 0,
                'gain': 4,
                'white_balance_temperature': 4500,
                'sharpness': 0,
            }],
            remappings=[('image_raw', '/image_raw'),
                        ('camera_info', '/camera_info')],
            condition=IfCondition(with_camera),
        ),

        # NO republisher here any more. usb_cam already advertises
        # /image_raw/compressed itself through image_transport, so the
        # image_transport/republish node was a SECOND publisher on the same
        # topic: `ros2 topic info /image_raw/compressed -v` reported
        # "Publisher count: 2" and `topic hz` read 8.1 Hz for a 4 fps camera.
        # Every frame crossed the WiFi twice, and this Pi 3B paid for two JPEG
        # encodes of the identical image. It became redundant when the driver
        # switched from v4l2_camera to usb_cam (c5dbcf1) and was never removed.
        #
        # KNOWN GAP: with_stream:=false (what competition.launch.py uses to keep
        # video off the air during a run) used to work by not starting this
        # node. Since usb_cam publishes compressed on its own, that flag has in
        # fact been a no-op ever since c5dbcf1 -- removing the node does not
        # regress it, but it does not fix it either. Suppressing the transport
        # properly needs image_transport's `disable_pub_plugins` parameter on
        # the driver, which is worth doing before the competition.

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

        # Plain browser preview of the camera -- see web_stream.py. Runs
        # regardless of with_stream (that flag is about ROS bandwidth to a
        # laptop; this is a local HTTP server on the Pi's own WiFi link, not
        # ROS traffic) but obviously needs with_camera for there to be
        # anything on /image_raw/compressed to show.
        Node(
            package='ttb3_perception',
            executable='web_stream',
            name='web_stream',
            output='screen',
            parameters=[{'port': web_stream_port}],
            condition=IfCondition(PythonExpression(
                ["'", with_web_stream, "' == 'true' and '",
                 with_camera, "' == 'true'"])),
        ),
    ])
