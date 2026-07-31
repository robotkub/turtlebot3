#!/usr/bin/env bash
# Step 1 of the mapping workflow (SRS section 10). Run on the ROBOT (the Pi).
# Starts wheels, lidar, IMU -- the robot's own senses and motors. Leave this
# window open; steps 2 and 3 run on the laptop.
set -euo pipefail

if [ -z "${ROS_DISTRO:-}" ]; then
  echo "ROS_DISTRO is not set -- open a new terminal (or 'source ~/.bashrc') first."
  exit 1
fi

echo "Starting TurtleBot3 robot bringup (model: ${TURTLEBOT3_MODEL:-unset})..."
echo "Leave this running. On the laptop, run ./2_map_start.sh next."
exec ros2 launch turtlebot3_bringup robot.launch.py
