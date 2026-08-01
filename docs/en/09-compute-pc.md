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
- **Visualization**: Handled via Foxglove Bridge (`visualize:=true`) bundled into the launch files (connecting via WebSocket on `ws://localhost:8765`), eliminating the need for RViz in the container.

---

## One-Time Setup

Build the Docker compute image on your laptop (from the repository root):

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

2. **On your Laptop**: Launch Cartographer mapping inside Docker, telling it how to reach the router:
   ```bash
   ROS_DOMAIN_ID=42 ROBOT_IP=<pi's current ip> docker compose run --rm ttb3-compute \
     ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true
   ```

3. **Visualize & Drive**:
   - Open Foxglove Studio (`ws://localhost:8765`) to view the map building in real time.
   - In a separate terminal on the laptop, teleop the robot interactively:
     ```bash
     docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard
     ```
     (The `stdin_open: true` / `tty: true` in `docker-compose.yml` ensures keystrokes are forwarded to the process.)
   - When finished, press `Ctrl-C` on the mapping terminal. The map files (`arena_v1.pgm` and `arena_v1.yaml`) will be saved directly into `./maps/` on your host laptop filesystem via mounted volume (`./maps:/maps`).

---

## Workflow 2: Standalone Nav2 Debug & Tuning

To test/tune Nav2 localization and path planning against a saved map:

1. **On the Pi**: bring up the robot base. The zenoh router runs automatically via systemd, nothing to start:
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **On your Laptop**: Run Nav2 standalone in Docker:
   ```bash
   ROS_DOMAIN_ID=42 ROBOT_IP=<pi's current ip> docker compose run --rm ttb3-compute \
     ros2 launch ttb3_bringup navigation.launch.py map:=/maps/arena_v1.yaml visualize:=true
   ```

3. **Visualize & Set Poses**:
   - Connect Foxglove to `ws://localhost:8765`.
   - Set 2D Pose Estimates and Navigation Goals via Foxglove.

---

## Key Requirements & Configuration

- **`ROS_DOMAIN_ID`**: Must match between the Pi and laptop (default `42`). Set via environment variable before running `docker compose run`.
- **`ROBOT_IP`**: Required — the Pi's current IP, so the container's zenoh session can connect (unicast TCP) to the router on the Pi.
- **RMW Middleware**: Uses `rmw_zenoh_cpp` matched on both ends. The router runs on the Pi as a systemd service (`zenoh-router.service`, installed by `install-humble-turtlebot3.sh`) so it's always up -- check with `systemctl status zenoh-router.service`. Manual/foreground start (`zenoh_router_start`) still exists for debugging.
- **Host Volume Mounting**: Host directory `./maps` is mounted to `/maps` inside the container, ensuring generated maps land on your host filesystem.

---

← [8. Foxglove](08-foxglove.md) | [Back to index](00-index.md)
