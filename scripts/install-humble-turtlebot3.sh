#!/usr/bin/env bash
#
# install-humble-turtlebot3.sh
# ROS2 Humble + TurtleBot3 + Foxglove Bridge — full setup for WRG2026 build
#
# THIS SCRIPT IS FOR THE RASPBERRY PI ONLY.
# Laptop teammates do NOT run this script — they use Docker exclusively.
# See docs/en/09-compute-pc.md for the Docker workflow.
#
# Fixed from the original snippet:
#   - "sudu apt upgrade" typo -> "sudo apt upgrade"
#   - added rosdep init/update (missing — colcon build fails without it)
#   - added TurtleBot3 packages (were missing entirely)
#   - was installing ros-humble-desktop-full everywhere, including on the
#     Pi — that drags in GUI/simulation/demo packages the Pi (headless
#     server) will never use. Pi always gets ros-humble-ros-base. This
#     project uses Foxglove as its only visualizer, not a desktop GUI.
#   - added Foxglove Bridge (optional visualizer, per request)
#   - added Zenoh (recommended RMW for TurtleBot3 -- unicast TCP to a
#     router, so it survives WiFi/Docker setups where DDS's UDP multicast
#     discovery doesn't reach, e.g. Docker Desktop on Mac/Windows)
#   - added workspace creation + build
#   - all ~/.bashrc edits are idempotent: safe to re-run this script anytime
#     without duplicating lines
#
# Usage (on the Pi):
#   chmod +x install-humble-turtlebot3.sh
#   ./install-humble-turtlebot3.sh        # only target is pi; arg is optional
#   ./install-humble-turtlebot3.sh pi     # also fine — same result
#
# After it finishes: close and reopen your terminal (or `source ~/.bashrc`)
#
set -euo pipefail

# ---------------------------------------------------------------------------
# [0/8] Accept optional "pi" argument for backwards-compat muscle memory,
#        but do nothing different with it — this script is Pi-only now.
# ---------------------------------------------------------------------------
TARGET="${1:-pi}"

if [ "$TARGET" != "pi" ]; then
  echo "ERROR: This script only runs on the Raspberry Pi (robot)."
  echo "Laptop teammates use Docker — see docs/en/09-compute-pc.md."
  exit 1
fi

echo "=================================================="
echo " Installing for: Raspberry Pi (robot)"
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

echo "=== [3/8] Update + upgrade ==="
sudo apt update -y
sudo apt upgrade -y

echo "=== [4/8] Install ROS2 Humble base + build tools ==="
# ros-base = ROS2 core + client libraries only. No desktop GUI packages --
# the Pi has no display attached, so none of that is usable here anyway.
# Saves real disk space and a lot of install time.
sudo apt install -y \
  ros-humble-ros-base \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-dev-tools

# rosdep init/update — required before "rosdep install" works in any workspace.
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init
fi
rosdep update

echo "=== [5/8] Install TurtleBot3 + navigation packages ==="
# Nav2/SLAM computation happens on the Pi during the actual competition run.
# joy/teleop-twist-joy/turtlebot3-teleop/twist-mux are needed here too --
# navigation.launch.py (now with teleop + joy + twist_mux for manual
# override of Nav2) is included by debug.launch.py and competition.launch.py,
# both of which run bare-metal on the Pi, not in Docker.
sudo apt install -y \
  ros-humble-turtlebot3 \
  ros-humble-turtlebot3-msgs \
  ros-humble-turtlebot3-teleop \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox \
  ros-humble-dynamixel-sdk \
  ros-humble-apriltag \
  ros-humble-apriltag-ros \
  ros-humble-image-transport-plugins \
  ros-humble-compressed-image-transport \
  ros-humble-v4l2-camera \
  ros-humble-rmw-zenoh-cpp \
  ros-humble-joy \
  ros-humble-teleop-twist-joy \
  ros-humble-twist-mux

# Servo dispenser control (drops the supply boxes) runs off Pi GPIO.
# gpiozero is the API; lgpio is its backend that works on Pi 5 too
# (RPi.GPIO does not). Harmless on Pi 3/4 as well.
sudo apt install -y python3-gpiozero python3-lgpio

echo "=== [5b/8] Stable address for the robot (mDNS) ==="
# The Pi's IP is DHCP and moves constantly -- it has several APs saved, and
# the competition venue is a different network again. Rather than hardcode a
# static IP (which breaks the moment the robot joins any other network, and
# can lock you out of a headless robot entirely), give it a stable NAME:
# avahi advertises "<hostname>.local", which follows the Pi onto whatever
# network it lands on. The laptop's ./ttb3 resolves that name automatically,
# so ROBOT_IP normally never has to be typed or updated.
sudo apt install -y avahi-daemon avahi-utils
sudo systemctl enable --now avahi-daemon
echo "  this robot answers to: $(hostname).local"
echo "  (check from the laptop with: ping $(hostname).local)"

echo "=== [6/8] Install Foxglove Bridge (optional visualizer) ==="
# The bridge runs on the Pi (it's the thing being connected TO by Foxglove Studio).
sudo apt install -y ros-humble-foxglove-bridge

echo "=== [7/8] Create + build TurtleBot3 workspace ==="
WS_DIR="$HOME/turtlebot3_ws"
mkdir -p "$WS_DIR/src"
cd "$WS_DIR"
# ROS2's setup.bash references unset vars internally -- incompatible with
# this script's `set -u`. Disable nounset just for the source.
set +u
source /opt/ros/humble/setup.bash
set -u
if [ -d src ] && [ -z "$(ls -A src)" ]; then
  echo "  (src/ is empty — add your team's packages here later, e.g. git clone)"
fi
# NOT --symlink-install: this workspace was originally built without it,
# and the ament_cmake_python symlink step then fails on the resulting
# directories (colcon tries to symlink over what's already a real
# directory from the earlier build) -- confirmed by actually hitting this
# on the robot. If you ever need symlink-install, `rm -rf build install
# log` first for a truly clean build.
colcon build || echo "  (nothing to build yet — that's fine on first run)"

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
# Remove any pre-existing RMW_IMPLEMENTATION line (e.g. a leftover
# rmw_cyclonedds_cpp export from before the Zenoh migration) before adding
# the current one -- otherwise add_once's exact-match check leaves both
# lines in ~/.bashrc, which happens to still work (last export wins) but
# is confusing to read.
sed -i '/^export RMW_IMPLEMENTATION=/d' "$HOME/.bashrc"
add_once "export RMW_IMPLEMENTATION=rmw_zenoh_cpp"
# Which lidar this robot has. LDS-01 is the older sensor and its driver
# (hls_lfcd_lds_driver) comes with turtlebot3-bringup via apt. If your unit is
# LDS-02/LD08 change this to LDS-02 (and build ld08_driver from source).
# robot.launch.py CRASHES if this is unset -- see docs chapter 2.
add_once "export LDS_MODEL=LDS-01"
# IMPORTANT: change this number so it's unique for your team at the competition
# (WRG has 6-7 teams sharing one WiFi AP per arena — same ID = you see each
# other's robots). Pick any number 0-101, agree on it with teammates.
add_once "export ROS_DOMAIN_ID=42"
add_once "alias rebuild='cd $WS_DIR && colcon build && source install/setup.bash'"
# reset_pose no longer hardcodes coordinates -- mission_manager republishes
# /initialpose from the ONE reference file (maps/start_pose.yaml).
add_once "alias reset_pose='ros2 service call /reset_to_start ttb3_msgs/srv/ResetToStart'"
add_once "alias estop='ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist \"{}\"'"
add_once "alias foxglove_start='ros2 launch foxglove_bridge foxglove_bridge_launch.xml'"
# Kept as a manual/foreground way to run the router (handy for debugging
# -- Ctrl-C it, tweak something, rerun). Normal operation doesn't need it:
# the systemd service below starts the router automatically on boot.
add_once "alias zenoh_router_start='ros2 run rmw_zenoh_cpp rmw_zenohd'"

echo ""

echo "=== [9/9] Install zenoh router as a systemd service (auto-starts on boot) ==="
# One zenoh router per system, run on the Pi -- everything else (this
# robot's own nodes, laptop Docker container) finds or connects to it.
# Running it as a systemd service means it's up before anyone logs in or
# runs robot.launch.py, and it restarts itself if it ever crashes --
# no more remembering to start it by hand.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sed "s|__USER__|$USER|g" "$SCRIPT_DIR/systemd/zenoh-router.service.template" \
  | sudo tee /etc/systemd/system/zenoh-router.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now zenoh-router.service
echo "  zenoh-router.service enabled + started."
echo "  Check anytime with: systemctl status zenoh-router.service"
echo ""

echo "=== [9b/9] Install hardware bringup as a systemd service (optional) ==="
# The Pi's job is now just drivers -- Nav2/perception/mission run on a laptop
# via `./ttb3 mission`. Since that half never changes, it may as well come up
# on boot: power the robot on and it is simply present on the ROS graph.
#
# Installed but NOT enabled by default. Enabling it means the motors and
# lidar go live the moment the Pi powers on, which is the wrong default while
# hardware is still being assembled and someone may be holding the robot.
# Turn it on deliberately, when the robot is built and you want it to behave
# like an appliance:
#     sudo systemctl enable --now ttb3-hardware.service
sed -e "s|__USER__|$USER|g" \
    -e "s|__WS__|$WS_DIR|g" \
    -e "s|__ARGS__||g" \
    "$SCRIPT_DIR/systemd/ttb3-hardware.service.template" \
  | sudo tee /etc/systemd/system/ttb3-hardware.service > /dev/null
sudo systemctl daemon-reload
echo "  ttb3-hardware.service installed (NOT enabled)."
echo "  Auto-start on boot with: sudo systemctl enable --now ttb3-hardware.service"
echo "  No camera/OpenCR yet? Edit ExecStart's args first, e.g."
echo "    with_camera:=false with_robot_base:=false"

echo "=== Done ==="
echo "Close and reopen your terminal, or run: source ~/.bashrc"
echo ""
echo "Quick checks once reopened:"
echo "  echo \$ROS_DISTRO         -> should print: humble"
echo "  echo \$TURTLEBOT3_MODEL   -> should print: burger"
echo "  ros2 pkg list | grep turtlebot3"
echo ""
echo "To visualize with Foxglove (optional, debug mode only):"
echo "  1. On the Pi:      foxglove_start"
echo "  2. On your laptop: open https://app.foxglove.dev (or the desktop app)"
echo "     -> Open connection -> Foxglove WebSocket -> ws://<PI_IP>:8765"
echo ""
echo "zenoh: router runs automatically via systemd (zenoh-router.service) --"
echo "  nothing to start by hand, it's up before you even log in, and"
echo "  restarts itself if it crashes. Check it with:"
echo "    systemctl status zenoh-router.service"
echo "  (the zenoh_router_start alias still exists for manual/foreground"
echo "   debugging if you ever need to stop the service and run it by hand)"
echo ""
echo "LAPTOP TEAMMATES: Do NOT run this script on your laptop."
echo "  Use Docker instead -- see docs/en/09-compute-pc.md."
echo ""
echo "Remember: set a UNIQUE ROS_DOMAIN_ID before competition day (edit ~/.bashrc)."
