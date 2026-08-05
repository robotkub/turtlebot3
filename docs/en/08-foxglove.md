← [7. Running the real mission](07-run-mission.md) | [Back to index](00-index.md)

# 8. Foxglove — Watching the Robot

Foxglove is a visualizer that runs in a **normal web browser** (or a desktop
app). It's how you see what the robot sees — the map, the lidar, the camera,
the mission state — from a laptop or even a phone, without ROS2 installed on it.

It's a **debug-mode tool only**. Never run it during an actual competition run
(it eats shared WiFi bandwidth — see [Chapter 7](07-run-mission.md)).

## Start the bridge (on the Pi)

The "bridge" is the piece that runs on the Pi and lets Foxglove connect to ROS.

- It starts **automatically** with `ros2 launch ttb3_bringup debug.launch.py`.
- Or start it by itself any time: `foxglove_start` (an alias the install script
  added to `~/.bashrc`).

It listens on port **8765**.

## Quick connect (one click, no dialog)

Foxglove can open a WebSocket connection straight from a URL — skip **Open
connection → Foxglove WebSocket → type the address** every time by just
bookmarking one of these:

| Scenario | Address | One-click link |
|---|---|---|
| Robot directly (debug/competition `foxglove_bridge`, running on the Pi) | `ws://192.168.1.127:8765` | <https://app.foxglove.dev/view?ds=foxglove-websocket&ds.url=ws%3A%2F%2F192.168.1.127%3A8765> |
| Laptop Docker container (mapping/Nav2 debug, [Chapter 9](09-compute-pc.md)) | `ws://localhost:8765` | <https://app.foxglove.dev/view?ds=foxglove-websocket&ds.url=ws%3A%2F%2Flocalhost%3A8765> |

`192.168.1.127` is this robot's current IP -- if it ever changes (new
network, DHCP reassigned it), re-check with `hostname -I` on the Pi and
swap the IP in the link (and in this table). Whichever layout you had open
last time loads automatically; see below to set up a dedicated one per
scenario once, and it'll stick.

Your laptop and the Pi must be on the same network with the same
`ROS_DOMAIN_ID` (see [Chapter 2](02-install.md)).

<!-- SCREENSHOT SLOT: the "Open connection -> Foxglove WebSocket -> ws://..." dialog.
     Save as assets/foxglove-images/connect-dialog.png and uncomment:
![Foxglove connection dialog](../../assets/foxglove-images/connect-dialog.png) -->

## Import a ready-made layout

Instead of building panels by hand, import one of the three we ship (one per
workflow). **Top bar → Layout menu → Import from file…**, then pick one:

| File | Use when | Panels |
|---|---|---|
| [`foxglove_layout.json`](../../src/ttb3_bringup/config/foxglove_layout.json) | Running `debug.launch.py` / `competition.launch.py` ([Chapter 7](07-run-mission.md)) | 3D (map/scan/tf) + camera Image + `/tag_detections`, `/victim_detections`, `/mission_status`, `/sensor_state` + Teleop |
| [`foxglove_layout_mapping.json`](../../src/ttb3_bringup/config/foxglove_layout_mapping.json) | Building a map with slam_toolbox ([Chapter 5](05-navigation.md), [Chapter 9](09-compute-pc.md)) | 3D showing the map growing (`/map`, `/scan`, the SLAM pose graph) + Teleop |
| [`foxglove_layout_nav.json`](../../src/ttb3_bringup/config/foxglove_layout_nav.json) | Tuning Nav2 (AMCL localization, costmaps, path planning) | 3D (map, costmaps, planned path, AMCL particle cloud) + `/amcl_pose` + "2D Pose Estimate" button + Teleop |

Copy the `.json` file to your laptop first, or open the repo there. Once
imported it's saved under your Foxglove account (or the team org, if you're
signed into one) and stays as the active layout for future one-click
connects (above) -- no need to re-import each session.

<!-- SCREENSHOT SLOT: the imported dashboard with all panels populated.
     Save as assets/foxglove-images/dashboard.png and uncomment:
![Foxglove dashboard](../../assets/foxglove-images/dashboard.png) -->

## Picking connection + layout together

Two separate choices every time you open Foxglove: **which connection**
(top-left, "Open connection" or a one-click link above) and **which layout**
(top bar, Layout dropdown -- pick from what you've already imported once,
no need to re-import). Picking the wrong pair doesn't error, panels just sit
empty because the topics don't match what's actually running.

| Doing this | Connection | Layout |
|---|---|---|
| Practicing the mission (`debug.launch.py`) | `ws://192.168.1.127:8765` | `foxglove_layout.json` |
| Building a map (`mapping.launch.py`, via Docker) | `ws://localhost:8765` | `foxglove_layout_mapping.json` |
| Tuning Nav2 (`navigation.launch.py`, via Docker) | `ws://localhost:8765` | `foxglove_layout_nav.json` |

<!-- SCREENSHOT SLOT: the Layout dropdown open, showing all three imported
     layouts to pick from. Save as assets/foxglove-images/layout-picker.png
     and uncomment:
![Foxglove layout picker](../../assets/foxglove-images/layout-picker.png) -->

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
| `/save_zone` | `ttb3_msgs/srv/SaveZone` | append a mission zone to `maps/mission_zones.yaml`. `{source: "click"}` uses the last point you clicked on the map, `{source: "robot"}` uses where the robot is standing (heading included) |
| `/clear_zones` | `std_srvs/srv/Trigger` | empty the zone list and start recording again |

The nav layout ships the **"Save mission point (robot here)"** button, so
importing `foxglove_layout_nav.json` covers the common case; add panels by hand
for the rest. `zone_recorder` hosts both zone services and runs under
`navigation.launch.py` as well as `debug.launch.py`, so recording zones works
in a plain `./ttb3 nav` session.

You can also **start the mission** without the physical button by publishing an
empty message to **`/mission_start`** (`std_msgs/msg/Empty`) from a Publish
panel — handy while bench-testing.

## Teleop safety

The Teleop panel publishes `/cmd_vel` directly, which **fights the mission's own
`/cmd_vel`** if the mission is running. Only teleop when the mission is in
`IDLE` or `DONE` (or after an e-stop), and be ready to e-stop. Only open one
Foxglove session driving `/cmd_vel` at a time.

---
← [7. Running the real mission](07-run-mission.md) | [Back to index](00-index.md)
