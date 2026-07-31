#!/usr/bin/env bash
# Step 3 of the mapping workflow (SRS section 10). Run on the LAPTOP once the
# map built by 2_map_start.sh looks complete. Saves it into turtlebot3_ws/maps/.
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: ./3_map_save.sh <name>   (e.g. ./3_map_save.sh arena_v1)"
  exit 1
fi
NAME="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAPS_DIR="${SCRIPT_DIR}/../maps"
mkdir -p "$MAPS_DIR"

OUT_PREFIX="${MAPS_DIR}/${NAME}"
echo "Saving map to ${OUT_PREFIX}.yaml + ${OUT_PREFIX}.pgm ..."
ros2 run nav2_map_server map_saver_cli -f "$OUT_PREFIX"

echo ""
echo "Done. To navigate using this map (debug.launch.py / competition.launch.py):"
echo "  ros2 launch ttb3_bringup debug.launch.py map:=${OUT_PREFIX}.yaml"
echo ""
echo "Or make it the default by editing the 'map' arg default in"
echo "  ttb3_bringup/launch/debug.launch.py / competition.launch.py"
