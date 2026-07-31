#!/usr/bin/env bash
#
# flash_opencr.sh -- one command to flash our CUSTOM OpenCR firmware from the Pi.
#
# Pulls the ROBOTIS OpenCR setup into a repeatable script (see the e-Manual:
# https://emanual.robotis.com/docs/en/platform/turtlebot3/opencr_setup/), using
# arduino-cli instead of the Arduino IDE so it's fully command-line:
#   1. install arduino-cli (if missing)
#   2. add the OpenCR board package + install the OpenCR core
#   3. apply our one-line patch that DISABLES the SW1/SW2 test-drive
#      (see disable_test_drive.patch) so the buttons are free for the mission
#   4. compile our sketch (turtlebot3_burger_custom) and upload it to OpenCR
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
SKETCH="$HERE/turtlebot3_burger_custom"
FQBN="OpenCR:OpenCR:OpenCR"
BOARD_URL="https://raw.githubusercontent.com/ROBOTIS-GIT/OpenCR/master/arduino/opencr_release/package_opencr_index.json"
PORT="${1:-}"

echo "=== [1/5] arduino-cli ==="
if ! command -v arduino-cli >/dev/null 2>&1; then
  echo "installing arduino-cli into ~/bin ..."
  mkdir -p "$HOME/bin"
  curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh \
    | BINDIR="$HOME/bin" sh
  export PATH="$HOME/bin:$PATH"
fi
arduino-cli version

echo "=== [2/5] OpenCR board package ==="
arduino-cli config init --overwrite >/dev/null 2>&1 || true
arduino-cli config add board_manager.additional_urls "$BOARD_URL" 2>/dev/null || \
  arduino-cli config set board_manager.additional_urls "$BOARD_URL"
arduino-cli core update-index
arduino-cli core install OpenCR:OpenCR

echo "=== [3/5] disable the SW1/SW2 test-drive in the OpenCR library ==="
# Find the library file the OpenCR core actually compiles.
TB3_CPP="$(find "$HOME/.arduino15/packages/OpenCR" \
  -path '*turtlebot3_ros2/src/turtlebot3/turtlebot3.cpp' 2>/dev/null | head -n1 || true)"
if [ -z "$TB3_CPP" ]; then
  echo "!! could not find turtlebot3.cpp under the installed OpenCR core."
  echo "   Flashing STOCK firmware would leave SW1/SW2 test-driving the robot."
  echo "   See disable_test_drive.patch and apply it by hand, then re-run."
  exit 1
fi
if grep -qE '^\s*test_motors_with_buttons\(' "$TB3_CPP"; then
  cp -n "$TB3_CPP" "$TB3_CPP.robotkub.bak" || true
  # comment out the test-drive call (idempotent)
  sed -i -E 's|^([[:space:]]*)test_motors_with_buttons\(|\1// RobotKub: disabled (mission buttons) // test_motors_with_buttons(|' "$TB3_CPP"
  echo "patched: $TB3_CPP"
else
  echo "already patched (no active test_motors_with_buttons call): $TB3_CPP"
fi

echo "=== [4/5] detect port ==="
if [ -z "$PORT" ]; then
  PORT="$(arduino-cli board list 2>/dev/null | awk '/ttyACM/{print $1; exit}')"
  PORT="${PORT:-/dev/ttyACM0}"
fi
echo "using port: $PORT"

echo "=== [5/5] compile + upload $SKETCH ==="
arduino-cli compile --fqbn "$FQBN" "$SKETCH"
arduino-cli upload  --fqbn "$FQBN" -p "$PORT" "$SKETCH"

echo ""
echo "=== done ==="
echo "Verify from ROS (robot base running):"
echo "  ros2 topic echo /sensor_state   # press SW1/SW2 -> 'button' changes, robot does NOT move"
