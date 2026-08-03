#!/bin/bash
set -e

# Source ROS 2 base environment
source "/opt/ros/humble/setup.bash"

# Source workspace install overlay
if [ -f "/ros2_ws/install/setup.bash" ]; then
    source "/ros2_ws/install/setup.bash"
fi

# Render the zenoh client config with the robot's current IP, so this
# session connects to the router on the Pi over unicast TCP instead of
# relying on multicast scouting (which Docker Desktop's VM networking
# blocks). See docker/zenoh_client_config.json5.template for why.
if [ "${RMW_IMPLEMENTATION:-}" = "rmw_zenoh_cpp" ]; then
    if [ -z "${ROBOT_IP:-}" ]; then
        echo "ros_entrypoint.sh: ROBOT_IP is not set but RMW_IMPLEMENTATION=rmw_zenoh_cpp -- set ROBOT_IP=<pi ip> so this container can reach the zenoh router" >&2
        exit 1
    fi
    export ZENOH_SESSION_CONFIG_URI=/tmp/zenoh_client_config.json5
    sed "s|\${ROBOT_IP}|${ROBOT_IP}|g" /zenoh_client_config.json5.template > "$ZENOH_SESSION_CONFIG_URI"
fi

exec "$@"
