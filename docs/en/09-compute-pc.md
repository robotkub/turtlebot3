← [8. Foxglove](08-foxglove.md) | [Back to index](00-index.md)

# 9. Offloading Mapping & Nav2 Debug Compute to Laptop (Docker)

The Raspberry Pi 3 B+ (quad-core ARM Cortex-A53 @ 1.4 GHz, 1 GB RAM) on the robot is resource-constrained. While it handles base motor control, sensors, perception, and mission logic well, running heavy SLAM (Cartographer) and Nav2 localization/planning alongside everything else during mapping and tuning can strain its resources.

To solve this during development and testing, mapping and standalone Nav2 debug compute are offloaded to a Docker container running on your laptop.

> [!IMPORTANT]
> **Debug/Testing Only!**
> This offloading path is for **mapping, tuning, and debug testing only**. During the actual competition run, `competition.launch.py` runs on the Pi completely standalone and autonomous (per SRS R10 / N3/N4 bandwidth constraints on shared competition WiFi).

---

## Architecture Overview

- **Physical Topology**: 2 physical machines — Raspberry Pi (on robot) + Laptop.
- **Laptop Environment**: Runs ROS 2 Humble containerized via Docker (`ttb3-compute`) rather than requiring a bare-metal ROS 2 desktop installation.
- **Networking**: `network_mode: host` enables native UDP multicast for ROS 2 DDS discovery across both machines.
- **Visualization**: Handled via Foxglove Bridge (`visualize:=true`) bundled into the launch files (connecting via WebSocket on `ws://localhost:8765`), eliminating the need for RViz in the container.

---

## One-Time Setup

Build the Docker compute image on your laptop (from the repository root):

```bash
docker compose build
```

This compiles `ttb3_bringup` inside a headless ROS 2 Humble base image pre-configured with Cartographer, Nav2, Foxglove Bridge, and CycloneDDS.

---

## Workflow 1: Building a Map (Cartographer + Map Autosaver)

1. **On the Pi**: Bring up the robot base (OpenCR bridge & Lidar):
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **On your Laptop**: Launch Cartographer mapping inside Docker:
   ```bash
   ROS_DOMAIN_ID=42 docker compose run --rm ttb3-compute \
     ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true
   ```

3. **Visualize & Drive**:
   - Open Foxglove Studio (`ws://localhost:8765`) to view the map building in real time.
   - On the laptop or Pi, teleop the robot:
     ```bash
     ros2 run turtlebot3_teleop teleop_keyboard
     ```
   - When finished, press `Ctrl-C` on the laptop terminal. The map files (`arena_v1.pgm` and `arena_v1.yaml`) will be saved directly into `./maps/` on your host laptop filesystem via mounted volume (`./maps:/maps`).

---

## Workflow 2: Standalone Nav2 Debug & Tuning

To test/tune Nav2 localization and path planning against a saved map:

1. **On the Pi**: Bring up the robot base:
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **On your Laptop**: Run Nav2 standalone in Docker:
   ```bash
   ROS_DOMAIN_ID=42 docker compose run --rm ttb3-compute \
     ros2 launch ttb3_bringup navigation.launch.py map:=/maps/arena_v1.yaml visualize:=true
   ```

3. **Visualize & Set Poses**:
   - Connect Foxglove to `ws://localhost:8765`.
   - Set 2D Pose Estimates and Navigation Goals via Foxglove.

---

## Key Requirements & Configuration

- **`ROS_DOMAIN_ID`**: Must match between the Pi and laptop (default `42`). Set via environment variable before running `docker compose run`.
- **DDS Middleware**: Uses `rmw_cyclonedds_cpp` matched on both ends for reliable discovery.
- **Host Volume Mounting**: Host directory `./maps` is mounted to `/maps` inside the container, ensuring generated maps land on your host filesystem.

---

← [8. Foxglove](08-foxglove.md) | [Back to index](00-index.md)
