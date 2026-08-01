← [1. Hardware + SD Card](01-hardware-setup.md) | [Back to index](00-index.md) | Next: [3. Git basics →](03-git-basics.md)

# 2. Installing the Software

## TL;DR — who runs what

| Machine | What to do |
|---|---|
| **Raspberry Pi (robot)** | Run the install script (one time, per the steps below) |
| **Laptop** | **Nothing to install** — use Docker. See [Chapter 9](09-compute-pc.md). |

Laptop teammates do **not** run `install-humble-turtlebot3.sh`. The Docker
workflow (`docker compose build` + `docker compose run`) gives you a complete
ROS2 Humble environment without fighting apt or managing a native ROS2 install.
It works the same on macOS, Windows, and Linux.

---

## 2.1 Run the install script (Pi only)

```bash
git clone https://github.com/robotkub/turtlebot3.git ~/turtlebot3_ws
cd ~/turtlebot3_ws/scripts
chmod +x install-humble-turtlebot3.sh
./install-humble-turtlebot3.sh
```

(New to `git clone`? Read [Chapter 3: Git basics](03-git-basics.md) first, then come back to this step.)

This installs on the Pi: ROS2 Humble base, TurtleBot3 packages, Nav2, SLAM Toolbox,
Cartographer, AprilTag, Foxglove Bridge, Zenoh (`rmw_zenoh_cpp`) — and builds
the workspace for you the first time. It also installs the servo
libraries (`python3-gpiozero`, `python3-lgpio`) for the dispenser, sets
`LDS_MODEL` and the handy aliases (`reset_pose`, `estop`, `foxglove_start`,
`rebuild`) in your `~/.bashrc`, and installs the **zenoh router as a systemd
service** (`zenoh-router.service`) so it's running before you even log in.

> [!IMPORTANT]
> Everything needs the zenoh router on the Pi to discover each other. On the
> Pi it's automatic (systemd) -- check with `systemctl status
> zenoh-router.service`. Laptop Docker containers connect to it via
> `ROBOT_IP=<pi ip>` — see [Chapter 9](09-compute-pc.md).

**After it finishes**: close and reopen your terminal (or `source ~/.bashrc`), then check:

```bash
echo $ROS_DISTRO         # -> humble
echo $TURTLEBOT3_MODEL    # -> burger
```

## 2.2 Set `LDS_MODEL` to match your real lidar (Pi only)

**Important** -- skip this and `robot.launch.py` will **crash immediately**
(`KeyError: 'LDS_MODEL'`) once you actually attach the robot, because it
reads this variable to decide which lidar driver to launch.

Check which lidar model you actually have (look for a sticker on the unit, or check your purchase spec):

| Model | Value to set | Driver used |
|---|---|---|
| LDS-01 (this project's hardware) | `LDS_MODEL=LDS-01` | `hls_lfcd_lds_driver` (already comes via apt) |
| LDS-02 / LD08 | `LDS_MODEL=LDS-02` | `ld08_driver` (must be cloned + built from source, not on apt) |

The install script already sets `LDS_MODEL=LDS-01` in your `~/.bashrc`. If your
unit is different, change it (and for LDS-02/LD08 you also need to build
`ld08_driver` from source):
```bash
grep LDS_MODEL ~/.bashrc          # confirm it's there
# to change it, edit ~/.bashrc, then:
source ~/.bashrc
```

> If you're on LDS-01 (this team's hardware), you're already done -- 
> `ros-humble-turtlebot3-bringup` pulls in `hls_lfcd_lds_driver` automatically
> via its apt dependency, and the install script set the env var.

## 2.3 ROS_DOMAIN_ID -- don't forget before competition day

The Pi's `~/.bashrc` (set by the install script) has `ROS_DOMAIN_ID=42`.
Laptop Docker runs pass it via `ROS_DOMAIN_ID=42 docker compose run ...`
(see [Chapter 9](09-compute-pc.md)) — **both must match**.
**Before the actual competition, every teammate must change it to a unique
number** (edit `~/.bashrc` on the Pi, and pass a matching value to every
`docker compose run`). The venue has 6-7 teams sharing one WiFi router --
keeping the default means you'll see (and interfere with) other teams' robots.

## 2.4 Build our workspace (Pi only)

If you haven't built yet (or changed code and want to rebuild):

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install
source install/setup.bash
```

Check our packages show up:
```bash
ros2 pkg list | grep ttb3
# should show: ttb3_bringup ttb3_dispenser ttb3_mission ttb3_msgs ttb3_perception
```

All good? Move on to [Chapter 3: Git basics](03-git-basics.md).

---
← [1. Hardware + SD Card](01-hardware-setup.md) | [Back to index](00-index.md) | Next: [3. Git basics →](03-git-basics.md)
