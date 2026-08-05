# maps/

Three kinds of file live here:

## Saved arena maps (`<name>.yaml` + `<name>.pgm`)

One pair per arena layout. Produced by the mapping launch, which **auto-saves
continuously and on Ctrl-C** -- no separate save step:

```bash
# on the Pi: robot's senses + motors
ros2 launch turtlebot3_bringup robot.launch.py

# on the laptop: export both once, every docker compose command below needs
# them (including `build` -- docker-compose.yml requires ROBOT_IP just to
# parse the file)
export ROS_DOMAIN_ID=42
export ROBOT_IP=<pi ip>

# SLAM + Foxglove Bridge + auto-saver, saving into this folder. Joy teleop is
# bundled in (muxed onto /cmd_vel via twist_mux).
docker compose run --rm --service-ports ttb3-compute \
  ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true

# for keyboard driving, run this SEPARATELY, in another terminal (same shell
# session so the exports above still apply) -- needs its own real TTY, which
# ros2 launch can't provide, so it can't be bundled into the launch above
docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard \
  --ros-args -r cmd_vel:=cmd_vel_teleop

# drive around until the map is complete, then Ctrl-C the mapping launch
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

## `mission_zones.yaml` -- the zone list (single source of truth)

Which locations the robot visits during `SEARCH`, in order (R1/R2/R4).
`mission_manager` drives to each zone in turn: arriving with nothing to see
moves on to the next one, seeing a tag or victim dispenses immediately and
then continues to the next zone -- `RETURN_HOME` only once every zone has
been visited (see [docs chapter 7](../docs/en/07-run-mission.md)).

The shipped file has four placeholder corners so the mission runs
end-to-end before real zones are known. Replace them with real coordinates
once you know where the tag and victim zones actually are.

Easiest way is from Foxglove, with `zone_recorder` running (it comes up with
both `navigation.launch.py` and `debug.launch.py`, so a plain `./ttb3 nav`
session is enough):

- **Click a spot on the map** with the 3D panel's point tool, then press
  **"Save mission point (clicked)"**. Foxglove's point tool carries no
  heading, so the zone is saved with `yaw: 0` -- pass a `yaw` in the service
  request, or edit it afterwards, if the robot needs to face a particular way.
- **Or drive the robot there** and press **"Save mission point (robot here)"**,
  which stores the live `/amcl_pose` including its heading.

Both append to the end of the list, so record them in visit order. From a
terminal it's the same service:

```bash
ros2 service call /save_zone ttb3_msgs/srv/SaveZone "{source: 'click', yaw: 0.0}"
ros2 service call /clear_zones std_srvs/srv/Trigger      # start over
```

Hand-editing is still perfectly fine. Note `mission_manager` reads this file
**once when it starts** (unlike `start_pose.yaml`, which it re-reads live), so
restart it to pick up newly recorded zones. An empty list falls back to the
four placeholders rather than doing nothing.
