# SKUBA TurtleBot3 -- WRG Thailand 2026

Autonomous TurtleBot3 Burger mission stack: build/load a map, read an AprilTag
number, drop that many supply boxes in front of the "victim" sign, return to
START. Full requirements: `SRS_TurtleBot3_WRG2026.docx` (team drive/Downloads).

No prior ROS2 experience assumed -- if a term doesn't make sense, check the
Glossary at the bottom.

## 1. Install (one-time, on BOTH the Pi and the laptop)

```bash
cd scripts
chmod +x install-humble-turtlebot3.sh
./install-humble-turtlebot3.sh
```

It auto-detects which machine it's on and installs the right thing:

- **On the Pi** (the robot): a lean, no-GUI install -- ROS2 Humble + TurtleBot3
  + Nav2 + SLAM + AprilTag + Foxglove Bridge. No RViz2 (the Pi has no screen).
- **On the laptop**: the same, plus the full desktop install (RViz2 + rqt) for
  viewing maps and debugging.

Force one or the other if auto-detect ever guesses wrong:
`./install-humble-turtlebot3.sh pi` or `./install-humble-turtlebot3.sh laptop`.

**After it finishes**: close and reopen your terminal (or `source ~/.bashrc`),
then check it worked:

```bash
echo $ROS_DISTRO         # -> humble
echo $TURTLEBOT3_MODEL    # -> burger
```

**Before competition day**: every teammate must edit `ROS_DOMAIN_ID` in their
own `~/.bashrc` to the same unique number (not the default `42`) -- WRG has
6-7 teams sharing one WiFi AP, and a shared default ID means you see (and
fight over) each other's robots.

## 2. Build the workspace

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install
source install/setup.bash
```

(the install script already does this once for you; re-run it yourself
whenever you edit code in `src/`)

## 3. Scripts reference

| Script | Runs on | What it does |
|---|---|---|
| `scripts/install-humble-turtlebot3.sh` | Pi or laptop | One-time setup (section 1 above) |
| `scripts/1_map_robot.sh` | **Pi** | Mapping step 1: starts wheels/lidar/IMU. Leave running. |
| `scripts/2_map_start.sh` | **laptop** | Mapping step 2: checks the robot is visible, then starts SLAM (Cartographer) + RViz2 |
| `scripts/mapping.launch.py` | laptop | Same job as `2_map_start.sh`, as a plain launch file (`ros2 launch scripts/mapping.launch.py`) -- doesn't need building, lives outside `src/` on purpose |
| `scripts/3_map_save.sh <name>` | laptop | Mapping step 3: saves the finished map into `maps/<name>.yaml` + `.pgm` |

Mapping only needs to be redone once per arena layout (redo it if the walls
move). Full walkthrough: `maps/README.md`.

Everything else -- actually running the mission -- is `ros2 launch`, not a
shell script:

```bash
ros2 launch ttb3_bringup debug.launch.py         # practice/tuning
ros2 launch ttb3_bringup competition.launch.py   # the real run
```

**Never test with the competition one, never compete with the debug one** --
see section 5. Full launch-arg reference (map path, mock-hardware toggle,
etc.): `src/ttb3_bringup/README.md`.

## 4. Packages (the code we wrote)

| Package | What it is |
|---|---|
| `ttb3_msgs` | Custom message/service definitions shared by everything else |
| `ttb3_perception` | `apriltag_detector` (reads the number tag) + `victim_detector` (finds the victim sign by color) |
| `ttb3_dispenser` | `dispenser_controller` -- drops the boxes (mock backend until the real hardware is wired up) |
| `ttb3_mission` | `mission_manager` (the "brain" -- the mission state machine) + `button_handler` (the two OpenCR buttons) |
| `ttb3_bringup` | Launch files, Nav2 wiring, Foxglove config |

## 5. Debug vs. competition mode

| | debug.launch.py | competition.launch.py |
|---|---|---|
| Used for | Practice, tuning, troubleshooting | Actual competition runs only |
| Camera stream to laptop? | Yes (compressed) | No -- off entirely |
| Foxglove/RViz2? | Yes | No |
| Network | Ethernet cable, static IP | WiFi only (unique `ROS_DOMAIN_ID`) |

This split exists because streaming video eats WiFi bandwidth the robot's own
navigation needs -- losing it mid-run can freeze the robot and force a
restart, which costs points. The camera driver itself still runs in
competition mode (the mission needs live images to find the tag/victim); only
the laptop-facing *stream* is switched off.

Neither launch file needs OpenCR/camera hardware attached to start today --
see `src/ttb3_bringup/README.md` for the `with_robot_base:=false
with_camera:=false` smoke-test args.

## 6. Opening the visualizer (Foxglove)

Foxglove is the recommended way to see what the robot is doing -- it runs in
a normal web browser (or desktop app), so you can check the robot from a
laptop with no ROS2 installed, or even a phone.

1. **On the Pi**: the bridge starts automatically with `debug.launch.py` (or
   run it by hand any time: `foxglove_start`, an alias already set up by the
   install script).
2. **On your laptop/phone**: open <https://app.foxglove.dev> (or the desktop
   app) -> "Open connection" -> **Foxglove WebSocket** -> `ws://<PI_IP>:8765`
   (find the Pi's IP with `hostname -I` on the Pi).
3. **Import the layout**: Layout panel -> Import from file ->
   `src/ttb3_bringup/config/foxglove_layout.json`. Gives you, in one screen:
   a 3D view (map/lidar/tf), the camera image, and live panels for the tag
   reading, victim detection, mission status, sensor/button state, plus a
   teleop widget on `/cmd_vel`.

RViz2 (on the laptop, via the Ethernet cable) is the alternative for debug
mode. **Use one or the other, never both at once** -- running both doubles
the WiFi bandwidth for no benefit. Foxglove/RViz2 are never used during an
actual competition run (see section 5).

## Glossary

| Term | Plain-English meaning |
|---|---|
| Node | One small program that does one job and talks to others via topics |
| Topic | A named channel nodes publish/subscribe to, like a group chat |
| SLAM | Simultaneously building a map AND figuring out where you are on it |
| AMCL | Figuring out where you are on a map you already have |
| Nav2 | Plans a path and drives the robot there, avoiding walls |
| AprilTag | A barcode-like marker a camera can read reliably, even at an angle |
| E-stop | "Emergency stop" -- immediately halt all motion (OpenCR button SW2) |
