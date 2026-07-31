← [7. OpenCR + Custom Firmware](07-opencr.md) | [Back to index](00-index.md)

# 8. Foxglove — Watching the Robot

Foxglove is a visualizer that runs in a **normal web browser** (or a desktop
app). It's how you see what the robot sees — the map, the lidar, the camera,
the mission state — from a laptop or even a phone, without ROS2 installed on it.

It's a **debug-mode tool only**. Never run it during an actual competition run
(it eats shared WiFi bandwidth — see [Chapter 6](06-run-mission.md)).

## Start the bridge (on the Pi)

The "bridge" is the piece that runs on the Pi and lets Foxglove connect to ROS.

- It starts **automatically** with `ros2 launch ttb3_bringup debug.launch.py`.
- Or start it by itself any time: `foxglove_start` (an alias the install script
  added to `~/.bashrc`).

It listens on port **8765**.

## Connect (on your laptop / phone)

1. Open **<https://app.foxglove.dev>** in a browser, or install the Foxglove
   desktop app.
2. Click **Open connection**.
3. Choose **Foxglove WebSocket**.
4. Enter `ws://<PI_IP>:8765` — find the Pi's IP with `hostname -I` on the Pi
   (e.g. `ws://192.168.1.127:8765`).

Your laptop and the Pi must be on the same network with the same
`ROS_DOMAIN_ID` (see [Chapter 2](02-install.md)).

<!-- SCREENSHOT SLOT: the "Open connection -> Foxglove WebSocket -> ws://..." dialog.
     Save as assets/foxglove-images/connect-dialog.png and uncomment:
![Foxglove connection dialog](../../assets/foxglove-images/connect-dialog.png) -->

## Import the ready-made layout

Instead of building panels by hand, import the layout we ship:

1. Top bar → **Layout** menu → **Import from file…**
2. Choose
   [`src/ttb3_bringup/config/foxglove_layout.json`](../../src/ttb3_bringup/config/foxglove_layout.json)
   (copy it to your laptop first, or open the repo there).

You'll get, in one screen:

| Panel | Shows |
|---|---|
| **3D** | the map, live lidar `/scan`, and the robot's TF frames |
| **Image** | the camera feed (`/image_raw/compressed`) |
| **Raw Messages** ×4 | `/tag_detections`, `/victim_detections`, `/mission_status`, `/sensor_state` |
| **Teleop** | drive the robot by publishing `/cmd_vel` |

<!-- SCREENSHOT SLOT: the imported dashboard with all panels populated.
     Save as assets/foxglove-images/dashboard.png and uncomment:
![Foxglove dashboard](../../assets/foxglove-images/dashboard.png) -->

## What to watch

- **`/mission_status`** — the single most useful panel. It shows the state
  machine live: `IDLE → INIT → SEARCH → APPROACH_VICTIM → DISPENSE →
  RETURN_HOME → DONE`, plus `boxes_dispensed`, `boxes_target`, and
  `estop_active`. If the robot isn't doing what you expect, look here first.
- **`/sensor_state`** — the `button` field changes when SW1/SW2 are pressed
  (a quick way to confirm the buttons + custom firmware work).
- **3D panel** — if the robot is "lost" (nav going wrong), check the lidar scan
  lines up with the map walls; if not, its localization is off (re-run
  `reset_to_start`, below).

## Calling services from Foxglove (start, reset, save start pose)

Add a **Service Call** panel (the "+" to add a panel → *Service Call*) to
trigger the robot without touching a terminal:

| Service | Type | What it does |
|---|---|---|
| `/reset_to_start` | `ttb3_msgs/srv/ResetToStart` | re-localize to the saved START pose (keeps mission progress) |
| `/save_start_pose` | `ttb3_msgs/srv/SaveStartPose` | capture the robot's *current* position as the new START (drive it there first) |

You can also **start the mission** without the physical button by publishing an
empty message to **`/mission_start`** (`std_msgs/msg/Empty`) from a Publish
panel — handy while bench-testing.

## Teleop safety

The Teleop panel publishes `/cmd_vel` directly, which **fights the mission's own
`/cmd_vel`** if the mission is running. Only teleop when the mission is in
`IDLE` or `DONE` (or after an e-stop), and be ready to e-stop. Use Foxglove
**or** RViz2, never both at once.

---
← [7. OpenCR + Custom Firmware](07-opencr.md) | [Back to index](00-index.md)
