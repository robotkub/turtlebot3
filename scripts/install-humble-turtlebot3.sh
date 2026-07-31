#!/usr/bin/env bash
#
# install-humble-turtlebot3.sh
# ROS2 Humble + TurtleBot3 + Foxglove Bridge — full setup for WRG2026 build
#
# Auto-detects whether it's running on the robot (Raspberry Pi, headless
# server) or on a laptop (has a desktop) and installs the right variant:
#
#   Pi/robot  -> ros-humble-ros-base  (no GUI packages — nothing to display)
#   Laptop    -> ros-humble-desktop   (adds RViz2, rqt — for visualizing)
#
# You can also force it: ./install-humble-turtlebot3.sh pi
#                         ./install-humble-turtlebot3.sh laptop
#
# Fixed from the original snippet:
#   - "sudu apt upgrade" typo -> "sudo apt upgrade"
#   - added rosdep init/update (missing — colcon build fails without it)
#   - added TurtleBot3 packages (were missing entirely)
#   - was installing ros-humble-desktop-full everywhere, including on the
#     Pi — that drags in Gazebo/RViz2/rqt/demos the Pi (headless server)
#     will never use. Now splits into a lean Pi install and a full
#     laptop install.
#   - added Foxglove Bridge (optional visualizer, per request)
#   - added CycloneDDS (recommended RMW for TurtleBot3)
#   - added workspace creation + build
#   - all ~/.bashrc edits are idempotent: safe to re-run this script anytime
#     without duplicating lines
#
# Usage:
#   chmod +x install-humble-turtlebot3.sh
#   ./install-humble-turtlebot3.sh          # auto-detects target
#   ./install-humble-turtlebot3.sh pi        # force Pi/headless install
#   ./install-humble-turtlebot3.sh laptop    # force laptop/desktop install
#
# After it finishes: close and reopen your terminal (or `source ~/.bashrc`)
#
set -euo pipefail

# ---------------------------------------------------------------------------
# [0/8] Figure out what machine we're on
# ---------------------------------------------------------------------------
TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  if grep -qi "raspberry pi" /proc/cpuinfo 2>/dev/null || \
     grep -qi "raspberry pi" /sys/firmware/devicetree/base/model 2>/dev/null; then
    TARGET="pi"
  else
    TARGET="laptop"
  fi
  echo "No target given — auto-detected: $TARGET"
  echo "(override anytime with: ./install-humble-turtlebot3.sh pi|laptop)"
fi

if [ "$TARGET" != "pi" ] && [ "$TARGET" != "laptop" ]; then
  echo "Unknown target '$TARGET'. Use: pi | laptop"
  exit 1
fi

echo "=================================================="
echo " Installing for target: $TARGET"
echo "=================================================="

echo "=== [1/8] Locale setup ==="
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
locale

echo "=== [2/8] Enable universe repo + ROS2 apt source ==="
sudo apt install -y software-properties-common
sudo add-apt-repository -y universe

sudo apt update && sudo apt install -y curl
ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

echo "=== [3/8] Update + upgrade (typo fixed: sudo, not sudu) ==="
sudo apt update -y
sudo apt upgrade -y

echo "=== [4/8] Install ROS2 Humble base + build tools ==="
if [ "$TARGET" == "pi" ]; then
  # ros-base = ROS2 core + client libraries only. No RViz2, no Gazebo,
  # no rqt — the Pi has no display attached, so none of that is usable
  # here anyway. Saves real disk space and a lot of install time.
  sudo apt install -y \
    ros-humble-ros-base \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-dev-tools
else
  # laptop: "desktop" (not "desktop-full") = ros-base + RViz2 + rqt.
  # Skips Gazebo/simulation packages by default — add turtlebot3-simulations
  # yourself later only if you actually want to test in simulation.
  sudo apt install -y \
    ros-humble-desktop \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-dev-tools
fi

# rosdep init/update — required before "rosdep install" works in any workspace.
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init
fi
rosdep update

echo "=== [5/8] Install TurtleBot3 + navigation packages ==="
# These run without any GUI, so both Pi and laptop get the same set —
# Nav2/SLAM computation happens on the Pi; the laptop just displays it.
sudo apt install -y \
  ros-humble-turtlebot3 \
  ros-humble-turtlebot3-msgs \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox \
  ros-humble-cartographer \
  ros-humble-cartographer-ros \
  ros-humble-dynamixel-sdk \
  ros-humble-apriltag \
  ros-humble-apriltag-ros \
  ros-humble-image-transport-plugins \
  ros-humble-compressed-image-transport \
  ros-humble-v4l2-camera \
  ros-humble-rmw-cyclonedds-cpp

if [ "$TARGET" == "pi" ]; then
  # Servo dispenser control (drops the supply boxes) runs off Pi GPIO.
  # gpiozero is the API; lgpio is its backend that works on Pi 5 too
  # (RPi.GPIO does not). Harmless on Pi 3/4 as well.
  sudo apt install -y python3-gpiozero python3-lgpio
fi

if [ "$TARGET" == "laptop" ]; then
  # Only useful on the laptop if you want to test navigation without the
  # real robot. Pulls in Gazebo — optional, comment out if you don't need it.
  sudo apt install -y ros-humble-turtlebot3-simulations
fi

echo "=== [6/8] Install Foxglove Bridge (optional visualizer) ==="
# The bridge itself runs on the Pi (it's the thing being connected TO).
# Installing it on the laptop too is harmless and lets you test locally.
sudo apt install -y ros-humble-foxglove-bridge

echo "=== [7/8] Create + build TurtleBot3 workspace ==="
WS_DIR="$HOME/turtlebot3_ws"
mkdir -p "$WS_DIR/src"
cd "$WS_DIR"
source /opt/ros/humble/setup.bash
if [ -d src ] && [ -z "$(ls -A src)" ]; then
  echo "  (src/ is empty — add your team's packages here later, e.g. git clone)"
fi
colcon build --symlink-install || echo "  (nothing to build yet — that's fine on first run)"

echo "=== [8/8] Fix ~/.bashrc (idempotent — safe to re-run) ==="

add_once() {
  # $1 = exact line to ensure exists in ~/.bashrc
  local line="$1"
  if ! grep -Fxq "$line" "$HOME/.bashrc"; then
    echo "$line" >> "$HOME/.bashrc"
  fi
}

add_once "# --- ROS2 Humble / TurtleBot3 (added by install-humble-turtlebot3.sh) ---"
add_once "source /opt/ros/humble/setup.bash"
add_once "if [ -f $WS_DIR/install/setup.bash ]; then source $WS_DIR/install/setup.bash; fi"
add_once "export TURTLEBOT3_MODEL=burger"
add_once "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
# Which lidar this robot has. LDS-01 is the older sensor and its driver
# (hls_lfcd_lds_driver) comes with turtlebot3-bringup via apt. If your unit is
# LDS-02/LD08 change this to LDS-02 (and build ld08_driver from source).
# robot.launch.py CRASHES if this is unset -- see docs chapter 2.
add_once "export LDS_MODEL=LDS-01"
# IMPORTANT: change this number so it's unique for your team at the competition
# (WRG has 6-7 teams sharing one WiFi AP per arena — same ID = you see each
# other's robots). Pick any number 0-101, agree on it with teammates.
add_once "export ROS_DOMAIN_ID=42"
add_once "alias rebuild='cd $WS_DIR && colcon build --symlink-install && source install/setup.bash'"
# reset_pose no longer hardcodes coordinates -- mission_manager republishes
# /initialpose from the ONE reference file (maps/start_pose.yaml).
add_once "alias reset_pose='ros2 service call /reset_to_start ttb3_msgs/srv/ResetToStart'"
add_once "alias estop='ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist \"{}\"'"
add_once "alias foxglove_start='ros2 launch foxglove_bridge foxglove_bridge_launch.xml'"

echo ""
echo "=== Done (installed as: $TARGET) ==="
echo "Close and reopen your terminal, or run: source ~/.bashrc"
echo ""
echo "Quick checks once reopened:"
echo "  echo \$ROS_DISTRO         -> should print: humble"
echo "  echo \$TURTLEBOT3_MODEL   -> should print: burger"
echo "  ros2 pkg list | grep turtlebot3"
if [ "$TARGET" == "laptop" ]; then
echo "  rviz2                    -> window should open"
fi
echo ""
echo "To visualize with Foxglove (optional, debug mode only — see SRS section 7):"
echo "  1. On the Pi:      foxglove_start"
echo "  2. On your laptop: open https://app.foxglove.dev (or the desktop app)"
echo "     -> Open connection -> Foxglove WebSocket -> ws://<PI_IP>:8765"
echo ""
echo "Remember: set a UNIQUE ROS_DOMAIN_ID before competition day (edit ~/.bashrc)."
