# ttb3_bringup

Launch files and Foxglove config for the WRG2026 mission stack.

## Launch files

The stack splits in two, by whether a node is bolted to hardware:

| Launch | Runs on | What it starts |
|---|---|---|
| `hardware.launch.py` | **the Pi** | robot base (OpenCR + lidar), camera driver, compressed stream, dispenser servo — drivers only, nothing that thinks |
| `mission.launch.py` | **the laptop** (or the Pi) | Nav2 + perception + `mission_manager` + `zone_recorder` + `button_handler` + Foxglove |

**This is the normal way to run the robot:**

```bash
# on the Pi
ros2 launch ttb3_bringup hardware.launch.py
# on the laptop
./ttb3 mission
```

The split exists because the whole stack on one Pi 3/4 saturates it — with
Nav2, apriltag and the mission nodes all running, the Pi kept answering ping
while `sshd` could no longer complete a banner exchange. Zenoh carries the
graph between the two machines, so neither half cares where the other runs.
The physical SW1/SW2 buttons still start and e-stop the mission, because
`button_handler` reads `/sensor_state` off the shared graph.

The all-in-one launches still exist and still work — they are just these two
composed, both landing on the Pi:

| Launch | What it starts |
|---|---|
| `debug.launch.py` | `hardware` + `mission`, camera stream and Foxglove on |
| `competition.launch.py` | same, no camera stream, no Foxglove (WiFi-only, autonomous) |
| `navigation.launch.py` | Nav2 (AMCL + planner) against a saved map + joystick teleop, muxed with Nav2's own output via `twist_mux` for manual override — for testing/tuning nav by itself |
| `mapping.launch.py` | SLAM (slam_toolbox, online-async) + Foxglove Bridge + `map_autosaver` + joystick teleop muxed via `twist_mux` — build a map, auto-saves on Ctrl-C |

Anything with `ros2 launch` in front of it runs **on the Pi**
(`ssh skuba@skuba.local`) — the laptop is Docker-only and has no native
`ros2`. The laptop-side entry point is `./ttb3`, further down.

`hardware.launch.py` can also come up **on boot**: the installer writes
`ttb3-hardware.service` but leaves it disabled, since live motors the instant
the Pi powers on is the wrong default while the robot is still being
assembled. Turn it on when you want appliance behaviour:

```bash
sudo systemctl enable --now ttb3-hardware.service
```

```bash
# practice / tuning -- camera stream + Foxglove on
ros2 launch ttb3_bringup debug.launch.py

# actual competition run -- no streaming, WiFi only, fully autonomous
ros2 launch ttb3_bringup competition.launch.py
```

`debug`/`competition` take the same override args if you need them:

| Arg | Default | When to change |
|---|---|---|
| `with_robot_base` | `true` | `false` if OpenCR isn't plugged in yet |
| `with_camera` | `true` | `false` if the USB webcam isn't plugged in yet |
| `use_mock_hardware` | `true` | `false` once the real dispenser servo is wired up |
| `map` | `~/turtlebot3_ws/maps/arena_v1.yaml` | point at a different saved map |
| `params_file` | `config/nav2_params.yaml` (the team's tunable copy) | if you start tuning Nav2 |

`mapping.launch.py` args: `map_path` (where to save; a bare name always resolves
into the maps folder regardless of launch directory) and `visualize` (default
`true`, launches Foxglove Bridge).

`navigation.launch.py` args: `map` (default `arena_v1.yaml` in the maps
folder -- auto-detects `/maps` in Docker or `~/turtlebot3_ws/maps`
bare-metal, same as `mapping.launch.py`), `params_file` (default
`config/nav2_params.yaml`), and `visualize` (default `true`, launches
Foxglove Bridge).

### Manual override while driving (mapping & navigation)

Both `mapping.launch.py` and `navigation.launch.py` bring up joystick teleop
(`joy` + `teleop_twist_joy`, `config/teleop_joy.yaml`) automatically,
publishing to `cmd_vel_joy`. A `twist_mux` node (`config/twist_mux_mapping.yaml`
/ `config/twist_mux_navigation.yaml`) arbitrates it against `cmd_vel_nav`
(Nav2, in `navigation.launch.py` only) onto the single `/cmd_vel` the robot
actually drives on.

Keyboard teleop is **not** launched automatically -- `ros2 launch` manages
child processes through pipes and can't give any of them the raw TTY that
`teleop_keyboard` needs to read keystrokes (confirmed: it crashes with
`termios.error: Inappropriate ioctl for device` if you try). Run it
separately, in its own terminal, remapped so twist_mux still picks it up:
```bash
docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard \
  --ros-args -r cmd_vel:=cmd_vel_teleop
```
Priority: **joy > keyboard > Nav2** -- grabbing the controller always
overrides the keyboard, and grabbing either always overrides autonomous
navigation. Joystick passthrough into the Docker container only works on
Linux hosts (`/dev/input` isn't passed through by Docker Desktop on
Mac/Windows) -- keyboard still works everywhere.

### Docker Compute Offloading (Mapping & Nav Debug)

Normally you just use the `./ttb3` wrapper at the repo root, which handles all
of the below: it finds the robot by name (`skuba.local` via mDNS, so a DHCP
change doesn't matter), reads `ROS_DOMAIN_ID` from `.env`, and remembers
`--service-ports`.
```bash
# `.env` is committed and usually needs no editing at all
./ttb3 build
./ttb3 map             # or: ./ttb3 nav / ./ttb3 teleop / replay / record
```

The raw form, for reference. `ROBOT_IP` must be a **literal IPv4 address**, not
`skuba.local` -- it feeds an unbracketed `tcp/${ROBOT_IP}:7447`, which can't
express the IPv6 a `.local` name answers with first. Get it with `hostname -I`
on the Pi, or just use `./ttb3`, which resolves the name for you every run:
```bash
# export BOTH vars first -- docker-compose.yml requires ROBOT_IP to even
# parse the file, so `docker compose build` needs it set too, not just `run`.
export ROS_DOMAIN_ID=42
export ROBOT_IP=<pi ip>

# Build compute container. ./src is mounted and the image uses
# --symlink-install, so params/launch/Python edits are live -- rebuild only for
# ttb3_msgs interface changes, new entry points, or apt changes.
docker compose build

# Mapping in Docker (saves to ./maps on host)
docker compose run --rm --service-ports ttb3-compute \
  ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true

# Standalone Nav2 debug in Docker
docker compose run --rm --service-ports ttb3-compute \
  ros2 launch ttb3_bringup navigation.launch.py visualize:=true
```

### Dispenser servo params (`dispenser_controller`)

The servo is on Pi GPIO. Defaults suit an SG90-style servo; override as needed:

| Param | Default | Meaning |
|---|---|---|
| `use_mock_hardware` | `true` | `false` = drive the real servo |
| `gate_pin` | `18` | BCM pin the servo signal wire is on (GPIO18 = physical pin 12) |
| `hold_angle` | `0.0` | gate-closed angle (deg) |
| `shoot_angle` | `180.0` | fire-one-cube angle (deg) |
| `settle_time_sec` | `0.7` | dwell at each angle (tune so exactly one cube launches) |

Right now (no OpenCR/camera/dispenser physically attached), smoke-test with:

```bash
ros2 launch ttb3_bringup debug.launch.py with_robot_base:=false with_camera:=false
```

This still brings up Nav2, all five mission nodes (mock dispenser), and the
Foxglove bridge, so you can check everything wires up cleanly before the
chassis is assembled.

## Foxglove

1. On the Pi: `foxglove_start` (alias already in `~/.bashrc`), or it's already
   included automatically by `debug.launch.py`.
2. On your laptop/phone: open <https://app.foxglove.dev> (or the desktop app),
   "Open connection" -> Foxglove WebSocket -> `ws://<PI_IP>:8765`.
3. Import `config/foxglove_layout.json` (Layout panel -> Import from file) for
   a ready-made dashboard: 3D view (map/scan/tf), camera image, AprilTag /
   victim / mission-status / sensor-state raw message panels, and a teleop
   panel on `/cmd_vel`.
4. Only open one Foxglove session driving `/cmd_vel` at a time -- running two
   doubles the WiFi bandwidth for no benefit.

Foxglove is debug-only. `competition.launch.py` never starts the bridge or
any camera streaming -- the camera driver still runs since the
mission itself needs live images, only the laptop-facing stream is removed.

## Manual hardware checklist (once the chassis exists)

None of this could be verified today -- no OpenCR, camera, or dispenser was
physically attached to the Pi during development:

- [ ] Real camera image looks reasonable in Foxglove (focus, exposure, FOV)
- [ ] AprilTag decodes reliably at the actual arena approach distance/angle
      (tune `size:` in `ttb3_perception/config/tags_36h11.yaml` to the real
      printed tag edge length)
- [ ] Victim sign (a human figure) reliably detected by the person detector at
      the real approach distance; adjust `confidence_threshold` in
      `ttb3_perception/config/victim_detector.yaml` if it misses / false-fires
- [ ] Servo wired to GPIO18 (physical pin 12), `use_mock_hardware:=false`,
      hold/shoot angles verified to drop exactly one cube
- [ ] Custom OpenCR firmware flashed (see `firmware/opencr/`) so SW1/SW2 don't
      test-drive the robot
- [ ] A real map recorded with `mapping.launch.py`, START pose captured via
      `/save_start_pose`, and `maps/mission_zones.yaml` set to real
      in-bounds zone coordinates — record those from Foxglove with
      `/save_zone` (click the map, or drive there) rather than typing
      coordinates in by hand; `mission_manager` reads the zone file at
      startup, so restart it afterwards
- [ ] SW1 (start/resume) / SW2 (e-stop) tested against the real `/sensor_state` topic
- [ ] `ROS_DOMAIN_ID` changed to a unique value in `~/.bashrc` before competition day
