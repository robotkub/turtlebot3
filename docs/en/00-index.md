# RobotKub TurtleBot3 -- Learning Guide (WRG Thailand 2026)

**[ ภาษาไทย ](../th/00-index.md)**

Welcome! This series walks through everything step by step -- from unboxing
the hardware to running the full mission autonomously. No prior ROS2
experience assumed.

## Learning goals

By the end of this series you should be able to:

- [ ] Use **git** (clone / pull / commit / push) well enough to maintain the team's code
- [ ] Understand how **Navigation** (SLAM, AMCL, Nav2) works, and where our code plugs into it
- [ ] Understand how **Vision** (reading the AprilTag, finding the victim sign) works, and where to tune it
- [ ] Flash the **OpenCR firmware** and understand why it's customized
- [ ] Use **Foxglove** to see what the robot sees and drive it from a laptop
- [ ] Run the **full mission end-to-end** yourself, in both debug and competition mode

## Table of contents

| Chapter | Content |
|---|---|
| [1. Hardware + SD Card Flash + WiFi](01-hardware-setup.md) | What you need, flashing the SD card, setting up WiFi/SSH before first boot |
| [2. Installing the software](02-install.md) | Running `install-humble-turtlebot3.sh`, setting `LDS_MODEL` to match your real lidar, building the workspace |
| [3. Git basics](03-git-basics.md) | clone/pull/commit/push, the workflow this team actually uses on this repo |
| [4. Understanding Navigation](04-navigation.md) | node/topic/TF, SLAM vs AMCL, Nav2, the mapping workflow, how `mission_manager` plugs in |
| [5. Understanding Vision](05-vision.md) | AprilTag detector, victim detector (color+contour), which config files to tune |
| [6. Running the real mission](06-run-mission.md) | debug vs competition launch, the start/e-stop/resume buttons, servo wiring, competition-day checklist |
| [7. OpenCR + Custom Firmware](07-opencr.md) | what OpenCR does, why we flash custom firmware (buttons), Arduino IDE flashing steps |
| [8. Foxglove](08-foxglove.md) | connecting the visualizer, importing the dashboard, calling services, watching mission state |

## Other reference docs in this project

- [`../../README.md`](../../README.md) -- the repo's main README (short summary, quick reference)
- [`../../src/ttb3_bringup/README.md`](../../src/ttb3_bringup/README.md) -- full launch argument reference + hardware checklist
- [`../../maps/README.md`](../../maps/README.md) -- about saved maps
- Full SRS: `SRS_TurtleBot3_WRG2026.docx`
- Official TurtleBot3 manual: <https://emanual.robotis.com/docs/en/platform/turtlebot3/overview/>

## Glossary

| Term | Plain-English meaning |
|---|---|
| Node | One small program that does one job and talks to others via topics |
| Topic | A named channel nodes publish/subscribe to, like a group chat |
| SLAM | Simultaneously building a map AND figuring out where you are on it |
| AMCL | Figuring out where you are on a map you already have |
| Nav2 | Plans a path and drives the robot there, avoiding walls |
| AprilTag | A barcode-like marker a camera can read reliably, even at an angle |
| E-stop | "Emergency stop" — immediately halt all motion (OpenCR button SW2) |

Not sure where to start? Start at [Chapter 1](01-hardware-setup.md).
