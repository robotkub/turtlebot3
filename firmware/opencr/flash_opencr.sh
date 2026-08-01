#!/usr/bin/env bash
#
# flash_opencr.sh -- one command to flash our CUSTOM OpenCR firmware from the Pi.
#
# Uploads the prebuilt, already-compiled prebuilt/turtlebot3_burger_custom.opencr
# over serial using tools/opencr_ld_shell_arm (ROBOTIS's own ARM uploader,
# vendored here -- see tools/README.md). No arduino-cli, no compiler, no
# internet connection needed on the Pi: this is a pure serial file transfer,
# so it just works on Raspberry Pi's ARM architecture.
#
# (If you need to REBUILD the .opencr file itself -- e.g. you changed
# turtlebot3_burger_custom.ino or disable_test_drive.patch -- that's a
# separate, maintainer-only step: see build_firmware.sh. That one does need
# an x86_64 toolchain the Pi can't run, which is exactly why we split "build"
# out from "flash": building happens once on a dev machine, flashing happens
# any time on the Pi with zero extra setup.)
#
# Run ON THE PI with OpenCR connected by USB:
#     cd ~/turtlebot3_ws/firmware/opencr
#     ./flash_opencr.sh                # auto-detect port
#     ./flash_opencr.sh /dev/ttyACM0   # or name the port
#
# Why custom firmware at all: stock firmware test-drives the robot on SW1/SW2
# (SW1 = forward 0.3 m, SW2 = spin 180). We use those buttons for
# start/e-stop/resume, so the robot must not move when they're pressed.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FW_FILE="$HERE/prebuilt/turtlebot3_burger_custom.opencr"
UPLOADER="$HERE/tools/opencr_ld_shell_arm"
PORT="${1:-}"

if [ ! -f "$FW_FILE" ]; then
  echo "!! $FW_FILE not found."
  echo "   Someone needs to run build_firmware.sh (on a dev machine) first"
  echo "   and commit prebuilt/turtlebot3_burger_custom.opencr."
  exit 1
fi

echo "=== [1/2] detect port ==="
if [ -z "$PORT" ]; then
  PORT="$(ls /dev/ttyACM* 2>/dev/null | head -n1 || true)"
  PORT="${PORT:-/dev/ttyACM0}"
fi
echo "using port: $PORT"

echo "=== [2/2] upload $FW_FILE ==="
chmod +x "$UPLOADER"
"$UPLOADER" "$PORT" 115200 "$FW_FILE" 1

echo ""
echo "=== done ==="
echo "Verify from ROS (robot base running):"
echo "  ros2 topic echo /sensor_state   # press SW1/SW2 -> 'button' changes, robot does NOT move"
