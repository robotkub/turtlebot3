# maps/

Saved SLAM maps (`<name>.yaml` + `<name>.pgm`), one pair per arena layout.
Produced by `../scripts/3_map_save.sh <name>`. Re-run the mapping workflow
(`../scripts/1_map_robot.sh` -> `2_map_start.sh` -> `3_map_save.sh`) whenever
the arena walls move.

Point `debug.launch.py` / `competition.launch.py` at a map with:
```
ros2 launch ttb3_bringup debug.launch.py map:=$(pwd)/arena_v1.yaml
```
