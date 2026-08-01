# ttb3_bringup

Launch files and Foxglove config for the WRG2026 mission stack. See
`~/Downloads/SRS_TurtleBot3_WRG2026.docx` for the full requirements this
implements.

## Launch files

| Launch | What it starts |
|---|---|
| `debug.launch.py` | full stack: robot base + camera (compressed stream) + navigation + mission nodes + Foxglove |
| `competition.launch.py` | same, but no camera stream / no Foxglove (WiFi-only, autonomous) |
| `navigation.launch.py` | Nav2 only (AMCL + planner) against a saved map — for testing/tuning nav by itself |
| `mapping.launch.py` | SLAM (Cartographer) + Foxglove Bridge + `map_autosaver` — build a map, auto-saves on Ctrl-C |

```bash
# practice / tuning -- camera stream + Foxglove on, LAN cable assumed
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

`navigation.launch.py` args: `map` (default `~/turtlebot3_ws/maps/arena_v1.yaml`), `params_file` (default `config/nav2_params.yaml`), and `visualize` (default `true`, launches Foxglove Bridge).

### Docker Compute Offloading (Mapping & Nav Debug)

To offload Cartographer mapping or Nav2 debug compute to your laptop:
```bash
# Build compute container (one-time)
docker compose build

# Mapping in Docker (saves to ./maps on host)
ROS_DOMAIN_ID=42 ROBOT_IP=<pi ip> docker compose run --rm ttb3-compute \
  ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true

# Standalone Nav2 debug in Docker
ROS_DOMAIN_ID=42 ROBOT_IP=<pi ip> docker compose run --rm ttb3-compute \
  ros2 launch ttb3_bringup navigation.launch.py map:=/maps/arena_v1.yaml visualize:=true
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
   doubles the WiFi bandwidth for no benefit (SRS section 7).

Foxglove is debug-only. `competition.launch.py` never starts the bridge or
any camera streaming (N3/N4) -- the camera driver still runs since the
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
      `/save_start_pose`, and `waypoints_*` in
      `ttb3_mission/config/mission_params.yaml` set to real in-bounds coordinates
- [ ] SW1 (start/resume) / SW2 (e-stop) tested against the real `/sensor_state` topic
- [ ] `ROS_DOMAIN_ID` changed to a unique value in `~/.bashrc` before competition day (N5)
