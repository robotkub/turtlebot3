# maps/

Two kinds of file live here:

## Saved arena maps (`<name>.yaml` + `<name>.pgm`)

One pair per arena layout. Produced by the mapping launch, which **auto-saves
continuously and on Ctrl-C** -- no separate save step:

```bash
# on the Pi: robot's senses + motors
ros2 launch turtlebot3_bringup robot.launch.py

# on the laptop (Docker): SLAM + Foxglove Bridge + auto-saver, saving into this folder
ROS_DOMAIN_ID=42 ROBOT_IP=<pi ip> docker compose run --rm ttb3-compute \
  ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true

# on the laptop (Docker): drive around until the map is complete, then Ctrl-C the launch above
docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard
```

Re-do it whenever the arena walls move. Point a mission launch at a map with:
```bash
ros2 launch ttb3_bringup debug.launch.py map:=$(pwd)/arena_v1.yaml
```

## `start_pose.yaml` -- the START pose (single source of truth)

Where the robot begins and returns to (R6/R8). **Everything reads this one
file**, so you set it once. Capture it for real once you have a map + running
navigation:

```bash
# drive/place the robot on the START box, confirm it's well localized, then:
ros2 service call /save_start_pose ttb3_msgs/srv/SaveStartPose
```

That overwrites `start_pose.yaml` with the robot's current AMCL pose.
`mission_manager` re-reads it live (no rebuild). Hand-editing the `x/y/yaw` is
fine too. See [docs chapter 5](../docs/en/05-navigation.md).
