# ttb3_bringup

Launch files and Foxglove config for the WRG2026 mission stack. See
`~/Downloads/SRS_TurtleBot3_WRG2026.docx` for the full requirements this
implements.

## Running

```bash
# practice / tuning -- camera stream + Foxglove on, LAN cable assumed
ros2 launch ttb3_bringup debug.launch.py

# actual competition run -- no streaming, WiFi only, fully autonomous
ros2 launch ttb3_bringup competition.launch.py
```

Both take the same override args if you need them:

| Arg | Default | When to change |
|---|---|---|
| `with_robot_base` | `true` | `false` if OpenCR isn't plugged in yet |
| `with_camera` | `true` | `false` if the USB webcam isn't plugged in yet |
| `use_mock_hardware` | `true` | `false` once the real dispenser is wired up |
| `map` | `~/turtlebot3_ws/maps/arena_v1.yaml` | point at a different saved map |
| `params_file` | TurtleBot3's stock `burger.yaml` | if you start tuning Nav2 |

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
4. Use Foxglove **or** RViz2, never both at once -- running both doubles the
   WiFi bandwidth for no benefit (SRS section 7).

Foxglove is debug-only. `competition.launch.py` never starts the bridge or
any camera streaming (N3/N4) -- the camera driver still runs since the
mission itself needs live images, only the laptop-facing stream is removed.

## Manual hardware checklist (once the chassis exists)

None of this could be verified today -- no OpenCR, camera, or dispenser was
physically attached to the Pi during development:

- [ ] Real camera image looks reasonable in Foxglove/RViz (focus, exposure, FOV)
- [ ] AprilTag decodes reliably at the actual arena approach distance/angle
      (tune `size:` in `ttb3_perception/config/tags_36h11.yaml` to the real
      printed tag edge length)
- [ ] Victim sign's real HSV color sampled and set in
      `ttb3_perception/config/victim_color.yaml`
- [ ] Dispenser hardware decided and `ttb3_dispenser/hardware/gpio_backend.py`
      implemented, then `use_mock_hardware:=false`
- [ ] A real map recorded via `turtlebot3_ws/scripts/` (see its README) and
      `search_waypoints` in `ttb3_mission/config/mission_params.yaml` updated
      to real in-bounds coordinates
- [ ] SW1/SW2 tested against the real `/sensor_state` topic
- [ ] `ROS_DOMAIN_ID` changed to a unique value in `~/.bashrc` before competition day (N5)
