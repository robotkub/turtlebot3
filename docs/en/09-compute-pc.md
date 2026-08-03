← [8. Foxglove](08-foxglove.md) | [Back to index](00-index.md)

# 9. Laptop Compute via Docker (the Only Laptop Path)

The Raspberry Pi 3 B+ (quad-core ARM Cortex-A53 @ 1.4 GHz, 1 GB RAM) on the robot is resource-constrained. While it handles base motor control, sensors, perception, and mission logic well, running heavy SLAM (Cartographer) and Nav2 localization/planning alongside everything else during mapping and tuning can strain its resources.

Laptop teammates offload this compute to a Docker container — **no native ROS 2
installation is needed or wanted on the laptop**. Docker makes the workflow
OS-agnostic: the same commands work on macOS, Windows, and Linux, so no one
has to fight `apt` or manage a separate ROS2 install on their personal machine.

> [!IMPORTANT]
> **Debug/Testing Only!**
> This offloading path is for **mapping, tuning, and debug testing only**. During the actual competition run, `competition.launch.py` runs on the Pi completely standalone and autonomous (per SRS R10 / N3/N4 bandwidth constraints on shared competition WiFi).

---

## Architecture Overview

- **Physical Topology**: 2 physical machines — Raspberry Pi (on robot) + Laptop.
- **Laptop Environment**: Runs ROS 2 Humble containerized via Docker (`ttb3-compute`). **No bare-metal ROS 2 installation needed or wanted on the laptop.**
- **Networking / RMW**: Uses **Zenoh** (`rmw_zenoh_cpp`), not CycloneDDS. A zenoh router runs on the Pi; the laptop container connects to it over plain **unicast TCP** (`ROBOT_IP:7447`), not multicast discovery.
  > [!IMPORTANT]
  > We switched away from CycloneDDS because its UDP multicast discovery does not work through Docker Desktop on Mac/Windows — `network_mode: host` there is *not* a real host network (Docker Desktop runs containers inside a VM), so multicast never reaches the robot even though it looks like it should. Zenoh's explicit unicast connect sidesteps this entirely; see `docker/zenoh_client_config.json5.template`.
- **Visualization**: Handled via Foxglove Bridge (`visualize:=true`) bundled into the launch files (connecting via WebSocket on `ws://localhost:8765`). Foxglove is the only visualizer used in this project.

```mermaid
graph TB
    subgraph Pi["🤖 Raspberry Pi (on robot)"]
        direction TB
        ZR["zenoh-router.service\n(systemd — auto-starts on boot)"]
        RB["robot.launch.py\n(OpenCR bridge, lidar, camera)"]
        MI["mission_manager\n+ perception nodes"]
        FB["foxglove_bridge\n:8765 (debug mode only)"]
        ZR --- RB
        RB --- MI
        MI --- FB
    end

    subgraph Laptop["💻 Laptop (any OS)"]
        direction TB
        DC["docker compose run ttb3-compute"]
        MAP["mapping.launch.py\n(Cartographer SLAM +\njoy + twist_mux)"]
        NAV["navigation.launch.py\n(Nav2 + AMCL +\njoy + twist_mux)"]
        TP["teleop_keyboard\n(separate terminal --\nneeds its own real TTY)"]
        FOX["Foxglove Studio\nws://localhost:8765"]
        DC --> MAP
        DC --> NAV
        DC --> TP
        FOX -.- DC
    end

    Pi <-->|"Zenoh unicast TCP\nROBOT_IP:7447\n(WiFi)"| Laptop
    FB -.->|"WebSocket :8765"| FOX
```

---

## One-Time Setup

Export `ROS_DOMAIN_ID` and `ROBOT_IP` first, in the shell you'll run every
`docker compose` command from -- `docker-compose.yml` requires `ROBOT_IP` to
even parse the file, so `build` needs it set too, not just `run` (a `build`
without it fails with "required variable ROBOT_IP is missing a value", and
if that happens the image silently stays stale -- any `run` afterwards uses
the old image instead of failing loudly):

```bash
export ROS_DOMAIN_ID=42
export ROBOT_IP=<pi's current ip>
```

Then build the Docker compute image on your laptop (from the repository root;
rerun after pulling code changes):

```bash
docker compose build
```

This compiles `ttb3_bringup` inside a headless ROS 2 Humble base image pre-configured with Cartographer, Nav2, Foxglove Bridge, TurtleBot3 teleop, and Zenoh.

---

## Workflow 1: Building a Map (Cartographer + Map Autosaver)

1. **On the Pi**: bring up the robot base (OpenCR bridge & Lidar). The zenoh router runs automatically via systemd, nothing to start:
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **On your Laptop**: Launch Cartographer mapping inside Docker (reuses the `ROS_DOMAIN_ID`/`ROBOT_IP` exported in One-Time Setup above -- export them again if this is a new shell):
   ```bash
   docker compose run --rm --service-ports ttb3-compute \
     ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true
   ```

3. **Visualize & Drive**:
   - Open Foxglove Studio (`ws://localhost:8765`) to view the map building in real time.
   - A joystick/gamepad comes up automatically inside `mapping.launch.py` (Linux hosts only -- Docker Desktop on Mac/Windows doesn't pass through `/dev/input`), muxed onto `/cmd_vel` via `twist_mux`.
   - For keyboard driving, run `teleop_keyboard` in its **own separate terminal** -- it needs raw control of a real TTY to read keystrokes, and `ros2 launch` can't provide that to a bundled child process (confirmed: it crashes with `termios.error` if you try):
     ```bash
     docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard \
       --ros-args -r cmd_vel:=cmd_vel_teleop
     ```
     (The `stdin_open: true` / `tty: true` in `docker-compose.yml` ensures keystrokes are forwarded to this process. Joy outranks keyboard if you run both.)
   - When finished, press `Ctrl-C` on the mapping terminal. The map files (`arena_v1.pgm` and `arena_v1.yaml`) will be saved directly into `./maps/` on your host laptop filesystem via mounted volume (`./maps:/maps`).

---

## Workflow 2: Standalone Nav2 Debug & Tuning

To test/tune Nav2 localization and path planning against a saved map:

1. **On the Pi**: bring up the robot base. The zenoh router runs automatically via systemd, nothing to start:
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **On your Laptop**: Run Nav2 standalone in Docker (reuses the exported `ROS_DOMAIN_ID`/`ROBOT_IP` from One-Time Setup):
   ```bash
   docker compose run --rm --service-ports ttb3-compute \
     ros2 launch ttb3_bringup navigation.launch.py visualize:=true
   ```

3. **Visualize & Set Poses**:
   - Connect Foxglove to `ws://localhost:8765`.
   - Set 2D Pose Estimates and Navigation Goals via Foxglove.
   - Joy teleop is also bundled into `navigation.launch.py`, muxed against Nav2's own output via `twist_mux` (joy > keyboard > Nav2 priority) -- grab the controller at any moment to override Nav2, e.g. to nudge the robot out of a stuck recovery. For keyboard, run `teleop_keyboard` separately as in Workflow 1 above (same TTY limitation).

---

## Key Requirements & Configuration

- **`ROS_DOMAIN_ID`**: Must match between the Pi and laptop (default `42`). Set via environment variable before running `docker compose run`.
- **`ROBOT_IP`**: Required — the Pi's current IP, so the container's zenoh session can connect (unicast TCP) to the router on the Pi.
- **RMW Middleware**: Uses `rmw_zenoh_cpp` matched on both ends. The router runs on the Pi as a systemd service (`zenoh-router.service`, installed by `install-humble-turtlebot3.sh`) so it's always up -- check with `systemctl status zenoh-router.service`. Manual/foreground start (`zenoh_router_start`) still exists for debugging.
- **Host Volume Mounting**: Host directory `./maps` is mounted to `/maps` inside the container, ensuring generated maps land on your host filesystem.

---

← [8. Foxglove](08-foxglove.md) | [Back to index](00-index.md)
