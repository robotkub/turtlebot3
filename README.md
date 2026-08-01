# RobotKub TurtleBot3 -- WRG Thailand 2026 (ROS League)

[![vision-tests](https://github.com/robotkub/turtlebot3/actions/workflows/vision-tests.yml/badge.svg)](https://github.com/robotkub/turtlebot3/actions/workflows/vision-tests.yml)
![ROS 2 Humble](https://img.shields.io/badge/ROS_2-Humble-22314E?logo=ros&logoColor=white)
![TurtleBot3](https://img.shields.io/badge/TurtleBot3-Burger-FF6C00)
![Python](https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-vision-5C3EE8?logo=opencv&logoColor=white)
![Zenoh](https://img.shields.io/badge/RMW-Zenoh-F37726)

Our team's software for the **ROS League / TurtleBot** event at the WRG Thailand
Championship -- a **TurtleBot3 Burger** running the arena mission **fully
autonomously**, no remote control once it starts.

## Start here: the tutorial series

**New to this project? Don't start with this README** -- start with the guided,
step-by-step tutorial (8 chapters, no prior ROS2 assumed), in Thai and English.
This README is just the quick reference.

- **ภาษาไทย: [`docs/th/00-index.md`](docs/th/00-index.md)**
- **English: [`docs/en/00-index.md`](docs/en/00-index.md)**

## What the robot has to do

![The competition arena](assets/arena/arena-layout.png)

The arena is a city of yellow roads with crosswalks, a **START** box (top-left),
and five green zones. The mission, in order:

1. **Drive out from START** and navigate the roads (using a map it built earlier).
2. **Read an AprilTag** in one of the zones (zones **2** and **3**) -- the tag's
   number tells the robot **how many supply boxes to drop**.
3. **Find a "victim" sign** (the people in zones **1** and **5**), drive up in
   front of it, and **dispense exactly that many boxes**.
4. **Return to START** before time runs out.

## What the robot detects

| ✅ Victim sign — a person, dispense here | ❌ Not a person — ignored | 🔢 AprilTag — box count |
|:---:|:---:|:---:|
| <img src="assets/arena/victim-sign.png" alt="The human victim sign" width="160"> | <img src="src/ttb3_perception/test/data/people/negative/arena_0.png" alt="Arena, not a person" width="160"> | <img src="src/ttb3_perception/test/data/apriltag/tag36h11_3.png" alt="AprilTag 3" width="120"> |
| The victim sign is a **human figure**. A MobileNet-SSD person detector finds it (whatever colour it wears) and the robot drives up to dispense. | The arena, tags and empty road aren't people -- the detector leaves them alone (no false trigger). | A 36h11 tag; its number (here **3**) is how many boxes to drop. |

How the detectors work, and how to tune them: [docs chapter 6](docs/en/06-vision.md).

## Learning objectives

This project is also how the team **learns ROS2**. Work through it and you should
be able to:

- Use **git** (clone / pull / commit / push) to maintain the team's code
- Understand **Navigation** -- SLAM, AMCL, Nav2 -- and how our mission code drives it
- Understand **Vision** -- reading the AprilTag and finding the victim sign (a human figure) with a person detector
- Flash and understand the **OpenCR firmware** (why the buttons are customized)
- Use **Foxglove** to see what the robot sees and drive it from a laptop
- Run the **full mission end-to-end**, in both debug and competition mode

## Running things

Zero-to-mission, in order. Do this once per robot/arena; after that, just the
last two commands (mission launch) for every practice run. Only one shell
script in the whole flow (the installer) -- everything else is `ros2 launch`
or a `ros2 service call`. Detail for every step is linked inline; the
[tutorial](#start-here-the-tutorial-series) walks through each with pictures.

**1. Clone the repo** (on both the Pi and your laptop):
```bash
git clone https://github.com/robotkub/turtlebot3.git ~/turtlebot3_ws
```

**2. Flash the OpenCR firmware** (on the Pi, OpenCR connected by USB) -- our
custom build, so the buttons don't test-drive the robot (see
[chapter 4](docs/en/04-opencr.md)):
```bash
cd ~/turtlebot3_ws/firmware/opencr
./flash_opencr.sh                # auto-detects the port
```

**3. Run the installer** (on the Pi, then again on your laptop --
[chapter 2](docs/en/02-install.md)):
```bash
cd ~/turtlebot3_ws/scripts
chmod +x install-humble-turtlebot3.sh
./install-humble-turtlebot3.sh
```

**4. Build a map** of the arena (once per layout -- robot base must be up on
the Pi first; auto-saves on Ctrl-C, see [chapter 5](docs/en/05-navigation.md) & [chapter 9](docs/en/09-compute-pc.md)):
```bash
zenoh_router_start                                       # on the Pi, separate terminal, leave running
ros2 launch turtlebot3_bringup robot.launch.py           # on the Pi, leave running

# Option A: Bare-metal ROS 2 on laptop
cd ~/turtlebot3_ws/maps
ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1

# Option B: Containerized Docker on laptop (no ROS 2 installation required on host)
docker compose build                                     # one-time image build
ROS_DOMAIN_ID=42 ROBOT_IP=<pi's current ip> docker compose run --rm ttb3-compute \
  ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true
```

**5. Save the START pose** -- drive/place the robot exactly on the START box,
confirm it's well localized (check Foxglove/RViz), then:
```bash
ros2 service call /save_start_pose ttb3_msgs/srv/SaveStartPose
```

**6. Run navigation** (or just launch the full mission below, which includes
this) -- against the map you just saved:
```bash
# Bare-metal
ros2 launch ttb3_bringup navigation.launch.py map:=~/turtlebot3_ws/maps/arena_v1.yaml

# Docker on laptop
ROS_DOMAIN_ID=42 ROBOT_IP=<pi's current ip> docker compose run --rm ttb3-compute \
  ros2 launch ttb3_bringup navigation.launch.py map:=/maps/arena_v1.yaml visualize:=true
```

**7. Run the mission**:
```bash
ros2 launch ttb3_bringup debug.launch.py         # practice/tuning
ros2 launch ttb3_bringup competition.launch.py   # the real run
```

**Never practice with the competition launch, never compete with the debug
one** -- see [docs chapter 7](docs/en/07-run-mission.md). Full launch-arg
reference: [`src/ttb3_bringup/README.md`](src/ttb3_bringup/README.md).

## Packages

| Package | What it is |
|---|---|
| `ttb3_msgs` | Custom message/service definitions shared by everything else |
| `ttb3_perception` | `apriltag_detector` (reads the number tag) + `victim_detector` (finds the victim sign -- a human figure -- with a MobileNet-SSD person detector) |
| `ttb3_dispenser` | `dispenser_controller` -- drops the boxes (mock backend until the real hardware is wired up) |
| `ttb3_mission` | `mission_manager` (the "brain" -- the mission state machine) + `button_handler` (the two OpenCR buttons) |
| `ttb3_bringup` | Launch files, Nav2 wiring, Foxglove config, `map_autosaver` |

The OpenCR firmware (flashed to the board, not a ROS package) lives in
[`firmware/opencr/`](firmware/opencr/).

## More

The tutorial is the real documentation; the detail for everything below lives there:

- Install & build -> [chapter 2](docs/en/02-install.md)
- OpenCR firmware (one-command flash) -> [chapter 4](docs/en/04-opencr.md)
- Navigation (SLAM / AMCL / Nav2) -> [chapter 5](docs/en/05-navigation.md)
- Vision + the **tests / CI** -> [chapter 6](docs/en/06-vision.md)
- Debug vs. competition mode, the buttons, servo, checklist -> [chapter 7](docs/en/07-run-mission.md)
- Foxglove -> [chapter 8](docs/en/08-foxglove.md)
- Laptop Docker compute offload -> [chapter 9](docs/en/09-compute-pc.md)
- Glossary of terms -> [index](docs/en/00-index.md#glossary)
