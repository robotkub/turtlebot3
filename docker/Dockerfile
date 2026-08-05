FROM ros:humble-ros-base

# Install slam_toolbox, Nav2, Foxglove bridge, Zenoh, teleop (keyboard + joystick),
# twist_mux (arbitrates cmd_vel between teleop/joy/nav) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-slam-toolbox \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-msgs \
    ros-humble-turtlebot3-teleop \
    ros-humble-joy \
    ros-humble-teleop-twist-joy \
    ros-humble-twist-mux \
    ros-humble-foxglove-bridge \
    ros-humble-rmw-zenoh-cpp \
    ros-humble-tf-transformations \
    ros-humble-apriltag-ros \
    ros-humble-apriltag-msgs \
    ros-humble-cv-bridge \
    ros-humble-image-transport-plugins \
    ros-humble-v4l2-camera \
    python3-opencv \
    ros-humble-rosidl-default-generators \
    python3-colcon-common-extensions \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws

# Copy ttb3_msgs too, not just ttb3_bringup -- without it, this container's
# foxglove_bridge can see custom-typed topics/services on the shared ROS
# graph (e.g. /save_start_pose from mission_manager on the Pi, same Zenoh
# domain) but can't resolve their type, and fails repeatedly with
# "package 'ttb3_msgs' not found".
COPY src/ttb3_msgs /ros2_ws/src/ttb3_msgs
# The mission stack. It is NOT robot-specific: mission.launch.py (Nav2 +
# perception + mission_manager) runs here so the Pi only has to drive
# hardware -- the full stack on one Pi 3/4 saturates it. ttb3_dispenser is
# included because mission_manager talks to it; its gpiozero import is lazy,
# so the mock backend runs fine on a laptop with no GPIO.
COPY src/ttb3_mission /ros2_ws/src/ttb3_mission
COPY src/ttb3_perception /ros2_ws/src/ttb3_perception
COPY src/ttb3_dispenser /ros2_ws/src/ttb3_dispenser
COPY src/ttb3_bringup /ros2_ws/src/ttb3_bringup

# Build the ttb3 packages we ship into the image
# --symlink-install so install/share/<pkg>/{config,launch} are symlinks back
# into /ros2_ws/src rather than copies. docker-compose.yml mounts the host's
# ./src over that path, so editing nav2_params.yaml or a launch file on the
# host takes effect on the next `./ttb3 nav` with NO rebuild. Without it,
# every param tweak needed a full image build to be seen.
#
# The COPY above still matters: the image has to build standalone (interface
# generation for ttb3_msgs, console_scripts entry points), and it's what makes
# the image usable if someone runs it without the mount.
RUN . /opt/ros/humble/setup.sh && \
    colcon build --symlink-install \
      --packages-select ttb3_msgs ttb3_bringup ttb3_mission \
                        ttb3_perception ttb3_dispenser

# Entrypoint script + zenoh client config template (see docker/ros_entrypoint.sh)
COPY docker/ros_entrypoint.sh /ros_entrypoint.sh
COPY docker/zenoh_client_config.json5.template /zenoh_client_config.json5.template
RUN chmod +x /ros_entrypoint.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
