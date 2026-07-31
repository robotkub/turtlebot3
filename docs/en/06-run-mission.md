← [5. Understanding Vision](05-vision.md) | [Back to index](00-index.md)

# 6. Running the Real Mission

## debug.launch.py vs. competition.launch.py

| | debug.launch.py | competition.launch.py |
|---|---|---|
| Used for | Practice / tuning / debugging | Actual competition runs only |
| Camera stream to laptop? | Yes (compressed) | No -- off entirely |
| Foxglove/RViz2? | Yes | No |
| Network | Ethernet cable, static IP | WiFi only (unique `ROS_DOMAIN_ID`) |

**Never practice with the competition one, never compete with the debug
one** -- streaming video eats the WiFi bandwidth the robot needs for its own
navigation. Losing that mid-run can freeze the robot and force a restart
(costing the bonus points).

## Testing today (no OpenCR/camera attached yet)

If the hardware isn't fully assembled yet, you can still test the software alone:

```bash
ros2 launch ttb3_bringup debug.launch.py with_robot_base:=false with_camera:=false
```

This brings up Nav2 + all 5 mission nodes (dispenser in mock mode) + the
Foxglove bridge, so you can verify everything is wired correctly before the
chassis is fully assembled.

## Hardware assembled -- running for real

```bash
# practice / tuning
ros2 launch ttb3_bringup debug.launch.py

# actual competition run
ros2 launch ttb3_bringup competition.launch.py
```

For the full list of other overridable args (map, params_file,
use_mock_hardware, etc.), see [`../../src/ttb3_bringup/README.md`](../../src/ttb3_bringup/README.md).

## Opening Foxglove to watch the robot

1. **On the Pi**: the bridge starts automatically with `debug.launch.py` (or run it manually: `foxglove_start`)
2. **On your laptop/phone**: open <https://app.foxglove.dev> (or the desktop app) ->
   "Open connection" -> **Foxglove WebSocket** -> `ws://<PI_IP>:8765`
   (find the Pi's IP with `hostname -I` on the Pi)
3. **Import the layout**: Layout panel -> Import from file ->
   `src/ttb3_bringup/config/foxglove_layout.json` -- gives you a 3D view
   (map/lidar/tf), the camera image, and panels for tag/victim/mission
   status/buttons plus a teleop widget, all in one screen

Use Foxglove **or** RViz2 (over Ethernet), never both at once -- running both
just doubles the WiFi bandwidth for no benefit. **Neither is ever used during
an actual competition run** (see the table above).

## Pre-competition checklist

- [ ] `ROS_DOMAIN_ID` changed to a unique number (see [Chapter 2](02-install.md), ROS_DOMAIN_ID section)
- [ ] A real arena map has been saved (`maps/arena_v1.yaml`), not a placeholder
- [ ] `search_waypoints`/`start_x,y,yaw` in `config/mission_params.yaml` match the real arena
- [ ] The real victim sign's color has been tuned (`config/victim_color.yaml`)
- [ ] The real AprilTag size has been measured and set in `config/tags_36h11.yaml`
- [ ] The real dispenser has been decided on and wired, `use_mock_hardware` turned off
- [ ] SW1 (reset pose) / SW2 (e-stop) tested against real hardware
- [ ] `competition.launch.py` run through a full end-to-end test at least once before the real thing

All checked? You're ready to compete. Back to the [table of contents](00-index.md).

---
← [5. Understanding Vision](05-vision.md) | [Back to index](00-index.md)
