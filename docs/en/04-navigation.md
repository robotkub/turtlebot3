← [3. Git basics](03-git-basics.md) | [Back to index](00-index.md) | Next: [5. Understanding Vision →](05-vision.md)

# 4. Understanding Navigation

## Basic vocabulary first

| Term | Plain-English meaning |
|---|---|
| **Node** | One small program that does one job, talks to others via topics |
| **Topic** | A named channel a node can publish (speak) to or subscribe (listen) to, e.g. `/cmd_vel` |
| **TF** | The system that answers "where is this point relative to that one," e.g. where the camera sits relative to the robot body |
| **`/odom`** | The robot's position as estimated from how much the wheels have turned (drifts if wheels slip) |
| **`/map`** | The arena map that's already been built |
| **SLAM** | Building a map AND figuring out where you are on it, at the same time (used when there's no map yet) |
| **AMCL** | Figuring out where you are on a map you **already have** (faster/more reliable than SLAM if the map doesn't change) |
| **Nav2** | Plans a path and drives there on its own, avoiding walls, once you give it a destination |

## The layers (bottom to top)

1. **OpenCR firmware** -- publishes `/odom`, `/imu`, `/scan` (lidar), `/sensor_state`; subscribes `/cmd_vel`
2. **ROS2** -- the messaging layer that lets every node talk to every other node
3. **Nav2 + SLAM/AMCL** -- off-the-shelf packages (we didn't write these) that we configure to work with our robot
4. **Our own code** -- `mission_manager` is the one telling Nav2 "go here" via the `NavigateToPose` action

## Building a map (once per arena layout)

Three scripts in `scripts/`, run in order:

| Step | Script | Runs on | What it does |
|---|---|---|---|
| 1 | `1_map_robot.sh` | **Pi** | Starts wheels/lidar/IMU -- leave it running |
| 2 | `2_map_start.sh` | **laptop** | Checks the robot is visible, then starts SLAM (Cartographer) + RViz2 |
| 3 | `3_map_save.sh <name>` | **laptop** | Saves the finished map into `maps/<name>.yaml` + `.pgm` |

```bash
# terminal 1 (Pi)
./scripts/1_map_robot.sh

# terminal 2 (laptop) -- wait for terminal 1 to be up first
./scripts/2_map_start.sh

# terminal 3 (laptop) -- drive the robot around the whole arena
ros2 run turtlebot3_teleop teleop_keyboard

# once the map in RViz has no black (unknown) areas left inside the walls
./scripts/3_map_save.sh arena_v1
```

More detail (e.g. troubleshooting when `/scan` isn't found): [`../../maps/README.md`](../../maps/README.md)

## How navigation works during an actual mission run

`ttb3_bringup`'s `debug.launch.py`/`competition.launch.py` bundle Nav2 bringup
(`nav2_bringup/bringup_launch.py`) with the saved map (`maps/arena_v1.yaml` by
default, override with `map:=...`). This mode uses **AMCL** (not SLAM) since
the map already exists -- no need to rebuild it every run.

## Where our code plugs into Nav2

Main file: `src/ttb3_mission/ttb3_mission/mission_manager.py`

- **SEARCH**: sends waypoints one at a time (from `config/mission_params.yaml`)
  to Nav2 via the `NavigateToPose` action, cycling through them until it sees
  both the tag and the victim sign
- **RETURN_HOME**: sends a goal back to the START coordinates (default matches
  the `reset_pose` alias in `.bashrc`)
- **Stuck watchdog**: checks `/odom` for real position movement over the last
  10 seconds; if there's been none (stuck on a wall / wheels spinning free),
  it cancels the goal and stops instead of pushing forever
- **ResetToStart service**: when SW1 is pressed, republishes `/initialpose` at
  the START pose (only corrects what AMCL believes -- doesn't erase any
  progress/score already made)

## Try it yourself

1. Launch debug mode (`ros2 launch ttb3_bringup debug.launch.py`) and watch `/mission_status` in Foxglove as the state changes
2. Try sending a manual goal: `ros2 topic pub -1 /initialpose ...` (reset the believed starting position)
3. Try pressing SW1/SW2 for real (or fake `/sensor_state` with `ros2 topic pub`) and watch the state change as expected

Ready? Move on to [Chapter 5: Understanding Vision](05-vision.md).

---
← [3. Git basics](03-git-basics.md) | [Back to index](00-index.md) | Next: [5. Understanding Vision →](05-vision.md)
