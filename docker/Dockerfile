FROM ros:humble-ros-base

# Install Cartographer, Nav2, Foxglove bridge, Zenoh, teleop (keyboard + joystick),
# twist_mux (arbitrates cmd_vel between teleop/joy/nav) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-cartographer \
    ros-humble-cartographer-ros \
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
COPY src/ttb3_bringup /ros2_ws/src/ttb3_bringup

# Build both packages
RUN . /opt/ros/humble/setup.sh && \
    colcon build --packages-select ttb3_msgs ttb3_bringup

# Entrypoint script + zenoh client config template (see docker/ros_entrypoint.sh)
COPY docker/ros_entrypoint.sh /ros_entrypoint.sh
COPY docker/zenoh_client_config.json5.template /zenoh_client_config.json5.template
RUN chmod +x /ros_entrypoint.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
