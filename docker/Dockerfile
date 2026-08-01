FROM ros:humble-ros-base

# Install Cartographer, Nav2, Foxglove bridge, CycloneDDS, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-cartographer \
    ros-humble-cartographer-ros \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-msgs \
    ros-humble-foxglove-bridge \
    ros-humble-rmw-cyclonedds-cpp \
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws

# Copy ttb3_bringup package into workspace
COPY src/ttb3_bringup /ros2_ws/src/ttb3_bringup

# Build ttb3_bringup package
RUN . /opt/ros/humble/setup.sh && \
    colcon build --packages-select ttb3_bringup

# Entrypoint script
COPY docker/ros_entrypoint.sh /ros_entrypoint.sh
RUN chmod +x /ros_entrypoint.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
