#!/usr/bin/env bash
# Step 2 of the mapping workflow (SRS section 10). Run on the LAPTOP, after
# 1_map_robot.sh is running on the Pi. Checks the robot is actually visible
# on the network first, then starts SLAM (Cartographer) + RViz2.
set -euo pipefail

if [ -z "${ROS_DISTRO:-}" ]; then
  echo "ROS_DISTRO is not set -- open a new terminal (or 'source ~/.bashrc') first."
  exit 1
fi

echo "Checking the robot is visible (waiting for /scan)..."
if ! timeout 10 ros2 topic list | grep -q '^/scan$'; then
  echo "  /scan topic not found."
  echo "  -> Is 1_map_robot.sh still running on the Pi?"
  echo "  -> Do the Pi and laptop have the SAME ROS_DOMAIN_ID (check ~/.bashrc on both)?"
  exit 1
fi
echo "  /scan found -- robot is visible."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Starting Cartographer + RViz2. Drive the robot around the whole arena:"
echo "  ros2 run turtlebot3_teleop teleop_keyboard"
echo "Once the map has no black (unknown) areas left inside the walls, run:"
echo "  ./3_map_save.sh <name>"
exec ros2 launch "${SCRIPT_DIR}/mapping.launch.py"
