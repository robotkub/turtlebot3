# RobotKub TurtleBot3 -- WRG Thailand 2026 (ROS League)

[![vision-tests](https://github.com/robotkub/turtlebot3/actions/workflows/vision-tests.yml/badge.svg)](https://github.com/robotkub/turtlebot3/actions/workflows/vision-tests.yml)

Our team's software for the **ROS League / TurtleBot** event at the WRG Thailand
Championship. This repo makes a **TurtleBot3 Burger** run the arena mission
**fully autonomously** -- no remote control once it starts.

## What the robot has to do

![The competition arena](assets/arena/arena-layout.png)

The arena is a city of yellow roads with crosswalks, a **START** box (top-left),
and five green zones. The mission, in order:

1. **Drive out from START** and navigate the roads (using a map it built earlier).
2. **Read an AprilTag** in one of the zones (zones **2** and **3** above) -- the
   tag's number tells the robot **how many supply boxes to drop**.
3. **Find a "victim" sign** (the people in zones **1** and **5**), drive up in
   front of it, and **dispense exactly that many boxes**.
4. **Return to START** before time runs out.

The victim sign is the yellow-shirted figures below -- our vision node finds it
by its **yellow** color:

<img src="assets/arena/victim-sign.png" alt="The victim sign" width="180">

Each of those steps is a separate ROS2 node; the [packages](#4-packages-the-code-we-wrote)
section lists them. Full written spec: `SRS_TurtleBot3_WRG2026.docx`.

## Learning objectives

This project is also how the team **learns ROS2**. Work through it and you should
be able to:

- Use **git** (clone / pull / commit / push) to maintain the team's code
- Understand **Navigation** -- SLAM, AMCL, Nav2 -- and how our mission code drives it
- Understand **Vision** -- reading the AprilTag and finding the victim sign by color
- Flash and understand the **OpenCR firmware** (why the buttons are customized)
- Use **Foxglove** to see what the robot sees and drive it from a laptop
- Run the **full mission end-to-end**, in both debug and competition mode

## Start here: the tutorial series

**New to this project? Don't start with this README** -- start with the guided,
step-by-step tutorial (8 chapters, no prior ROS2 assumed), written in **both
Thai and English**:

- 🇹🇭 **ภาษาไทย: [`docs/th/00-index.md`](docs/th/00-index.md)**
- 🇬🇧 **English: [`docs/en/00-index.md`](docs/en/00-index.md)**

It covers hardware + SD-card flashing, install, git, navigation, vision, running
the mission, OpenCR firmware, and Foxglove. This README is just the **quick
reference** for people who already know their way around.

No prior ROS2 experience assumed -- if a term doesn't make sense, check the
Glossary at the bottom, or the tutorial.

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

## 3. Running things

There's only one shell script — the installer. Everything else is `ros2 launch`.

```bash
# build a map (auto-saves on Ctrl-C; robot base must be up on the Pi first)
cd ~/turtlebot3_ws/maps
ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1

# run the mission
ros2 launch ttb3_bringup debug.launch.py         # practice/tuning
ros2 launch ttb3_bringup competition.launch.py   # the real run
```

Mapping only needs redoing once per arena layout. Full walkthrough:
[`maps/README.md`](maps/README.md) and
[docs chapter 4](docs/en/04-navigation.md).

**Never test with the competition one, never compete with the debug one** --
see section 5. Full launch-arg reference (map path, mock-hardware toggle,
servo params, etc.): [`src/ttb3_bringup/README.md`](src/ttb3_bringup/README.md).

## 3b. OpenCR firmware

The robot's OpenCR board runs lightly customized firmware (the two buttons are
mission controls: SW1 = start/resume, SW2 = e-stop — stock firmware would
test-drive the robot instead). Sketch + flashing steps:
[`firmware/opencr/`](firmware/opencr/) and [docs chapter 7](docs/en/07-opencr.md).

## 4. Packages (the code we wrote)

| Package | What it is |
|---|---|
| `ttb3_msgs` | Custom message/service definitions shared by everything else |
| `ttb3_perception` | `apriltag_detector` (reads the number tag) + `victim_detector` (finds the victim sign by color) |
| `ttb3_dispenser` | `dispenser_controller` -- drops the boxes (mock backend until the real hardware is wired up) |
| `ttb3_mission` | `mission_manager` (the "brain" -- the mission state machine) + `button_handler` (the two OpenCR buttons) |
| `ttb3_bringup` | Launch files, Nav2 wiring, Foxglove config, `map_autosaver` |

The Arduino firmware for the OpenCR board lives in `firmware/opencr/` (not a
ROS package — it's flashed to the board, see section 3b).

## 4b. Tests / CI

Every push runs the **vision tests** on GitHub Actions
(`.github/workflows/vision-tests.yml`, ~400 checks): they verify the AprilTag
reader gets the right number and that the victim detector finds the yellow sign
(and does **not** false-trigger on non-yellow people) across a bunch of test
images — the real reference photos plus generated synthetic figures — while
each image is **flipped, rotated in 90° steps, viewed from a high/low/side
angle (perspective), and randomly rotated/tilted/re-exposed**. AprilTags are
also checked at an angle. These tests are ROS-free (pure OpenCV + numpy +
pupil-apriltags), so they run fast without a ROS install. The detection logic
lives in `ttb3_perception/vision_core.py`; run them locally:

```bash
pip install -r src/ttb3_perception/test/requirements-test.txt
pytest src/ttb3_perception/test/test_vision.py -v
```

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

The full tutorial series now has **8 chapters** (adds OpenCR firmware + a
dedicated Foxglove chapter): [`docs/en/00-index.md`](docs/en/00-index.md) /
[`docs/th/00-index.md`](docs/th/00-index.md).
