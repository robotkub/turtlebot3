# RobotKub TurtleBot3 — WRG Thailand 2026 (ROS League)

[![vision-tests](https://github.com/robotkub/turtlebot3/actions/workflows/vision-tests.yml/badge.svg)](https://github.com/robotkub/turtlebot3/actions/workflows/vision-tests.yml)
![ROS 2 Humble](https://img.shields.io/badge/ROS_2-Humble-22314E?logo=ros&logoColor=white)
![TurtleBot3](https://img.shields.io/badge/TurtleBot3-Burger-FF6C00)
![Python](https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-vision-5C3EE8?logo=opencv&logoColor=white)
![Zenoh](https://img.shields.io/badge/RMW-Zenoh-F37726)

Our team's software for the **ROS League / TurtleBot** event at the WRG Thailand
Championship — a **TurtleBot3 Burger** running the arena mission **fully
autonomously**, no remote control once it starts.


<p align="center"> <img src="assets/turtlebot3/turtlebot3.png" alt="Turtlebot3" width=325 ></p>

## Start here: the tutorial series

**New to this project? Don't start with this README** — start with the guided,
step-by-step tutorial (8 chapters, no prior ROS2 assumed), in Thai and English.
This README is just the quick reference.

- **ภาษาไทย: [`docs/th/00-index.md`](docs/th/00-index.md)**
- **English: [`docs/en/00-index.md`](docs/en/00-index.md)**

## What the robot has to do

![The competition arena](assets/arena/arena-layout.png)

The arena is a city of yellow roads with crosswalks, a **START** box (top-left),
and five green zones. The mission, in order:

1. **Drive out from START** and navigate the roads (using a map it built earlier).
2. **Detect and dispense immediately**:
   - See an **AprilTag** in one of the tag zones (zones **2** or **3**) -> dispense
     that tag's number of boxes right away.
   - See a **"victim" sign** (human figure in zones **1** or **5**) without a tag ->
     drive up to it and dispense **1 box**.
3. **Return to START** before time runs out.

## What the robot detects

| ✅ Victim sign — a person, dispense 1 box here | ❌ Not a person — ignored | 🔢 AprilTag — dispense that tag's count |
|:---:|:---:|:---:|
| <img src="assets/arena/victim-sign.png" alt="The human victim sign" width="160"> | <img src="src/ttb3_perception/test/data/people/negative/arena_0.png" alt="Arena, not a person" width="160"> | <img src="src/ttb3_perception/test/data/apriltag/tag36h11_3.png" alt="AprilTag 3" width="120"> |
| The victim sign is a **human figure**. Seeing it triggers an immediate 1-box dispense (after walking up to it). | The arena, tags and empty road aren't people — the detector leaves them alone (no false trigger). | A 36h11 tag; its number (here **3**) is how many boxes to drop immediately upon sighting. |

How the detectors work, and how to tune them: [docs chapter 6](docs/en/06-vision.md).

## Learning objectives

This project is also how the team **learns ROS2**. Work through it and you should
be able to:

- Use **git** (clone / pull / commit / push) to maintain the team's code
- Understand **Navigation** — SLAM, AMCL, Nav2 — and how our mission code drives it
- Understand **Vision** — reading the AprilTag and finding the victim sign (a human figure) with a person detector
- Flash and understand the **OpenCR firmware** (why the buttons are customized)
- Use **Foxglove** to see what the robot sees and drive it from a laptop
- Run the **full mission end-to-end**, in both debug and competition mode

## Running things

Zero-to-mission, in order. Do this once per robot/arena; after that, just the
last two commands (mission launch) for every practice run. Only one shell
script in the whole flow (the installer) — everything else is `ros2 launch`
or a `ros2 service call`. Detail for every step is linked inline; the
[tutorial](#start-here-the-tutorial-series) walks through each with pictures.

**0. Install Docker** (laptop only).

On **macOS/Windows**, install Docker Desktop. On **Ubuntu**, this script sets
up Docker's official repo and installs the engine plus the compose plugin:

```bash
wget https://gitlab.com/-/snippets/3762780/raw/main/docker-install.sh
less docker-install.sh          # read it before running it
bash docker-install.sh
```

Then **add yourself to the `docker` group**. The installer script does *not* do this. Since `./ttb3` runs `docker compose` without `sudo`, skipping this step causes permission errors on the daemon socket:

```bash
sudo usermod -aG docker $USER
newgrp docker                   # or log out and back in
docker run --rm hello-world     # should work with no sudo
```

**1. Clone the repo** (on both the Pi and your laptop):
```bash
git clone https://github.com/robotkub/turtlebot3.git ~/turtlebot3_ws
```

**2. Flash the OpenCR firmware** (on the Pi, OpenCR connected by USB) — our
custom build, so the buttons don't test-drive the robot (see
[chapter 4](docs/en/04-opencr.md)):
```bash
cd ~/turtlebot3_ws/firmware/opencr
./flash_opencr.sh                # auto-detects the port
```

**3. Run the installer** on the **Pi only** — laptops use Docker instead
([chapter 2](docs/en/02-install.md)):
```bash
cd ~/turtlebot3_ws/scripts
chmod +x install-humble-turtlebot3.sh
./install-humble-turtlebot3.sh
```

**4. Build a map** of the arena (once per layout — robot base must be up on
the Pi first; auto-saves on Ctrl-C, see [chapter 5](docs/en/05-navigation.md) & [chapter 9](docs/en/09-compute-pc.md)):
You do not need to start anything on the Pi. `ttb3-hardware.service` automatically starts the base, lidar, dispenser, and speaker on boot. Do not launch it again by hand — a second `turtlebot3_node` conflicts with the first over `/dev/ttyACM0`.

```bash
# on your laptop -- no native ROS2 install needed, it all runs in Docker
# (nothing to configure: .env is committed, and finds the robot as skuba.local)
./ttb3 build            # once. src is mounted, so EDITS to params/launch/
                        #  Python are live. Rebuild for: a NEW file, msgs,
                        #  package.xml/setup.py, apt deps, or docker/
./ttb3 map              # SLAM + Foxglove + auto-saver
./ttb3 teleop           # keyboard driving, in a SECOND terminal
./ttb3 mission          # the full mission, thinking here instead of on the Pi

# testing one piece at a time, without the 40s full-stack bringup
./ttb3 detect           # "TAG 3  ->  3 boxes" -- is the camera reading tags?
./ttb3 test_servo       # fire the dispenser gate once
```
Joystick control is already included in `./ttb3 map`. Keyboard control needs its own terminal because `ros2 launch` cannot give a bundled node the real TTY it needs for keystrokes.

No robot sensors handy? `./ttb3 record` captures a session and `./ttb3 replay`
plays it back through the **whole** stack — bag, Nav2 and Foxglove from that
one command. The Pi still has to be powered **on** (its zenoh router carries
the traffic) but nothing needs to be plugged into it.

**5. Save the START pose** - `/save_start_pose` is hosted by `mission_manager`,
so something that starts it has to be running. `./ttb3 mission` on your laptop
is the easy way (the standalone `./ttb3 nav` does **not** start
`mission_manager`):
```bash
./ttb3 mission
```
AMCL self-localizes at (0, 0, 0) on startup (`set_initial_pose` in
`config/nav2_params.yaml`), which is the START box — slam_toolbox's map origin
is wherever the robot stood when mapping began. So the map appears in Foxglove
straight away; you do **not** normally need the pose-estimate tool. If
localization ever drifts badly, nudge it with the pose-estimate arrow tool in
Foxglove's 3D panel, or from the CLI:
```bash
ros2 topic pub -1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  '{header: {frame_id: "map"}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}'
```
Then drive/place the robot exactly on the START box, confirm it's well
localized (laser scan lines up with the map walls in Foxglove), and:
```bash
ros2 service call /save_start_pose ttb3_msgs/srv/SaveStartPose
```
From then on, `reset_to_start` re-publishes this saved pose automatically.

> **Import the Foxglove layout** (`config/foxglove_layout_nav.json`, Layout
> panel -> Import from file) before using the goal/pose tools. Foxglove's stock
> "Default" layout publishes goals to `/move_base_simple/goal` — the ROS 1
> name, which Nav2 does not listen on, so clicking "publish goal" silently
> does nothing. Our saved layout points at `/goal_pose` and `/initialpose`.
>
> Use the **web** app (<https://app.foxglove.dev>) or a current desktop build:
> `foxglove_bridge` 3.4.x speaks the newer `foxglove.sdk.v1` websocket
> subprotocol and rejects the legacy `foxglove.websocket.v1` outright (verified
> — a handshake offering only the old one gets `400 Bad Request`), so a
> long-outdated Studio will fail to connect for reasons that look like a
> network problem.

**6. Run navigation standalone** (optional — only for tuning Nav2 by itself;
skip straight to step 7 for normal practice runs, which already includes
this):
```bash
./ttb3 nav
```

Same as mapping: joystick teleop + `twist_mux` come up alongside Nav2 (keyboard
still needs its own separate terminal, see step 4), so you can grab manual
control at any moment and it immediately overrides autonomous driving
(joy > keyboard > Nav2 priority). No `mission_manager` here, so no
/save_start_pose — that's step 5, against `debug.launch.py`.

**7. Run the mission** — split across the two machines. The Pi drives hardware,
your laptop does the thinking:
```bash
# on your laptop. That's it -- the Pi is already running its half.
./ttb3 mission
```

The Pi's half (`hardware.launch.py`: base, lidar, dispenser, speaker) starts
on boot via `ttb3-hardware.service`, so there is nothing to run there and
nothing to remember. Only start it by hand if you've stopped the service:
`ros2 launch ttb3_bringup hardware.launch.py`.

We recommend running it this way (split across two machines). The full stack on one Pi 3/4 overloads it. Zenoh carries the graph between the two machines, physical SW1/SW2 buttons still work, and camera frames cross WiFi compressed.

Everything on the Pi still works if you want a self-contained robot — these
are just the two halves composed:
```bash
ros2 launch ttb3_bringup debug.launch.py         # practice/tuning
ros2 launch ttb3_bringup competition.launch.py   # the real run
```

The Pi half can also auto-start on boot (`ttb3-hardware.service`, installed
but left disabled — see [`src/ttb3_bringup/README.md`](src/ttb3_bringup/README.md)).

**Never practice with the competition launch, never compete with the debug
one** - see [docs chapter 7](docs/en/07-run-mission.md). Full launch-arg
reference: [`src/ttb3_bringup/README.md`](src/ttb3_bringup/README.md).

### If something looks broken

Each of these cost us real debugging time and fails in a way that points
somewhere else entirely — `./ttb3` exists mostly to make the first three
impossible to get wrong:

| Symptom | Cause |
|---|---|
| Foxglove stuck on "Waiting for connection…" | `docker compose run` publishes **no** ports without `--service-ports`; the bridge is running fine, nothing is forwarding 8765 |
| `required variable ROBOT_IP is missing` — even on `build` | `docker-compose.yml` needs `ROBOT_IP` just to *parse*. A failed `build` then leaves you silently running a stale image |
| Robot unreachable after it moved networks | Its IP is DHCP and changes. Use the name `skuba.local` (mDNS, set up by the installer), not a hardcoded address |
| `ssh skuba.local` -> "Permission denied", password retyped correctly | No username, so ssh used *your laptop's*. It's `ssh skuba@skuba.local` |
| `git pull` fails: *"Untracked working tree file '.env' would be overwritten by merge"* | `.env` is tracked now. `rm .env` and pull again — the committed one needs no editing |
| Banner says `robot: pinned …` when you expected `skuba.local -> …` | Something set `ROBOT_IP` — usually a leftover `.env` or an exported shell var. Any set `ROBOT_IP` is treated as a deliberate override |
| Everything starts, but nothing ever localizes, and the map never appears | AMCL has no pose, so there's no `map` frame for Foxglove to draw in. Fixed by `set_initial_pose`; if you disable that, you must send `/initialpose` yourself |
| "Publish goal" in Foxglove does nothing | You're on Foxglove's stock layout, which posts to the ROS 1 `/move_base_simple/goal`. Import `config/foxglove_layout_nav.json` |
| `termios.error: Inappropriate ioctl` from teleop | `teleop_keyboard` was launched by `ros2 launch`, which can't give it a real TTY. Run it on its own: `./ttb3 teleop` |
| `file 'x.launch.py' was not found in the share directory` for a file that plainly exists in `src/` | `--symlink-install` symlinks files **individually**, so a file added since the last image build has no symlink to follow. Editing an existing file is live; adding one needs `./ttb3 build` |
| Nav2 nodes hang at startup during a bag replay | No `/clock` yet. Replay needs `--clock` **and** `use_sim_time:=true`; `./ttb3 replay` does both |
| Bringup stops after `Activating controller_server` and **never** prints `Managed nodes are active` — no error at all | `local_costmap` waited longer for `odom → base_link` than zenoh's service timeout, so the lifecycle manager abandoned the reply and never advanced to `bt_navigator`. Nav2 sits half-activated and silently refuses every goal. Raised `queries_default_timeout` to 60s in `docker/zenoh_client_config.json5.template`. **`Managed nodes are active` is the go/no-go line — never send a goal before you see it** |
| AprilTag never detects anything, even though the camera image looks fine in Foxglove | `apriltag_node` needs **synchronized** `/image_raw` **and** `/camera_info`. Check its own counters in the log: `Synchronized pairs: 0` means it processed zero frames — it never even looked. `/camera_info` was being dropped on a saturated WiFi link. The camera now streams 320x240 @ 4fps for this reason |
| `GridBased: failed to create plan with tolerance 0.50`, then both recoveries abort with `Collision Ahead` | The **goal itself** is inside a wall, not the path. `zone_recorder` saves wherever the robot happens to be standing, which is usually far too close. A goal whose clearance is under the 0.10 m robot radius is a lethal cell that **no** `inflation_radius` can rescue. Check every zone's clearance before running — see below |
| Every goal "succeeds" in milliseconds, robot never moves, log shows `Transform data too old when converting from map to odom` | The Pi's clock disagrees with the laptop's. It has no RTC, so it boots at its last-known time if NTP hasn't landed. Nav2 can't transform the goal into `odom`, silently falls back to the origin — where odom already says the robot is — so the goal checker returns "reached" instantly. Check `timedatectl status` **on the Pi**: want `System clock synchronized: yes`. See [9a/9] in the installer |

### Checking mission zones before you drive

`maps/mission_zones.yaml` is just six poses, and nothing validates them. One
zone recorded 0.09 m from a wall — inside the robot's own 0.10 m radius — and
the whole mission stalled there while Nav2 reported a planning failure that
pointed nowhere near the real cause.

Clearance is the straight-line distance from a zone to the nearest occupied
cell in `maps/arena_v1.pgm`:

- **under 0.10 m** (robot radius) — lethal cell, the robot cannot stand there
  at all, and no `inflation_radius` setting changes that
- **under `inflation_radius`** — carries cost; NavFn may refuse it and the DWB
  critics may reject every trajectory
- **above both** — the planner has room

This arena is only 3.45 x 3.10 m, so Nav2's default 0.55 m inflation put over
a third of it under cost before the robot moved. It is 0.45 m here, and even
then every zone sits inside inflation — that is normal for a space this size,
and is fine as long as clearance clears the robot radius with margin.


### Testing one piece at a time

The full mission stack is a bad place to debug one component: bringup takes
~40s, the log fills with everything at once, and a localisation problem looks
identical to a camera problem until you have read three hundred lines. These
two commands isolate a single question each.

**`./ttb3 detect`** — perception only. No Nav2, no mission, nothing that
commands the base, so the robot cannot move while it is up. Hold a tag in
front of the camera and the answer prints as it changes:

```
[apriltag_detector]: no tag in view
[apriltag_detector]: TAG 3  ->  3 boxes
[apriltag_detector]: no tag in view
```

`box_count` is `clamp(tag_id + box_count_offset, 0, max_box_count)` — with the
defaults, tag 3 means 3 boxes. Output is edge-triggered; detections publish at
camera rate and printing every one would scroll the answer away.

foxglove_bridge is **off** by default here — it logs a line per topic on every
connection-graph tick, which buries the line you started the command to read.
Add `visualize:=true` when you need to see *where* the tag is, not just
whether it was read.

If nothing prints at all, read `apriltag_node`'s own counters first:

```
Image messages received:      32
CameraInfo messages received: 1
Synchronized pairs:           1
```

`apriltag_node` needs image **and** `camera_info` to arrive synchronized.
**`Synchronized pairs: 0` means it never looked at a single frame** — that is
a delivery problem, not a detection problem, and no amount of moving the tag
around will fix it.

**`./ttb3 test_servo [n]`** — fires the dispenser gate, printing
`/boxes_remaining` either side:

```
==> dispensing 1 box(es) via /dispense_command
  before: 5
  after:  4
```

It publishes the same `/dispense_command` the mission uses rather than a
bespoke test path, so it cannot drift from real behaviour. **Watch the robot,
not the terminal:** with `use_mock_hardware:=true` the count still decrements
even though no servo turned, so a pass here does not prove the hardware moved.


## Packages

| Package | What it is |
|---|---|
| `ttb3_msgs` | Custom message/service definitions shared by everything else |
| `ttb3_perception` | `apriltag_detector` (reads the number tag) + `victim_detector` (finds the victim sign — a human figure — with a MobileNet-SSD person detector) |
| `ttb3_dispenser` | `dispenser_controller` — drops the boxes (mock backend until the real hardware is wired up) |
| `ttb3_mission` | `mission_manager` (the "brain" — the mission state machine) + `button_handler` (the two OpenCR buttons) |
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
