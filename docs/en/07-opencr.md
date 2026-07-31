← [6. Running the real mission](06-run-mission.md) | [Back to index](00-index.md) | Next: [8. Foxglove →](08-foxglove.md)

# 7. OpenCR + Custom Firmware

## What OpenCR is

OpenCR is the robot's second brain — a microcontroller board (like a beefy
Arduino). While the Pi does the "thinking" (maps, vision, decisions), OpenCR
does the "reflexes": it spins the wheel motors at the exact speed it's told,
reads the IMU / wheel encoders / push buttons, and reports all of it to the Pi.

- It connects to the Pi by **USB** (shows up as `/dev/ttyACM0`).
- It runs **Arduino/C++ firmware**, flashed once and rarely changed.
- It publishes `/odom`, `/imu`, `/sensor_state` and subscribes `/cmd_vel`.

## Why we run *custom* firmware

Stock ROBOTIS firmware hard-codes a **test-drive on the push buttons** (handy
for checking motors during assembly):

- **SW1 → drives the robot forward ~0.3 m**
- **SW2 → spins it 180°**

But our mission needs those two buttons as controls:

| Button | Meaning (decided in ROS, not firmware) |
|---|---|
| **SW1** | **START** the mission (when idle) / **RESUME** (after an e-stop) |
| **SW2** | **E-STOP** — stop now, cancel navigation |

If we kept the stock firmware, the robot would lurch forward or spin every time
an operator touched a mission button. So we disable the built-in test-drive.
After the change the buttons **only report their state** on `/sensor_state`, and
[`button_handler`](../../src/ttb3_mission/ttb3_mission/button_handler.py) in ROS
decides what each press means.

That's the *only* change — a single commented-out line in one library file.
Everything else (motors, odometry, ROS communication) stays stock.

## The firmware lives in this repo

Everything you need is under [`firmware/opencr/`](../../firmware/opencr/):

- `turtlebot3_burger_custom/turtlebot3_burger_custom.ino` — the sketch you open and upload
- `disable_test_drive.patch` — the exact one-line change to make in the library
- `README.md` — the full build/flash walkthrough with file paths per OS

## Flashing, step by step

The visual walkthrough (with screenshots) is ROBOTIS's official OpenCR setup
page — follow it for the toolchain install:
**<https://emanual.robotis.com/docs/en/platform/turtlebot3/opencr_setup/>**

Short version:

1. **Install the Arduino IDE** (1.8.x or 2.x): <https://www.arduino.cc/en/software>
2. **Add the OpenCR board package**: File → Preferences → *Additional Boards
   Manager URLs* →
   `https://raw.githubusercontent.com/ROBOTIS-GIT/OpenCR/master/arduino/opencr_release/package_opencr_index.json`,
   then Tools → Board → Boards Manager → search **OpenCR** → Install.
3. **Make the one-line edit**: open the library's `turtlebot3.cpp` (path per OS
   is in [`firmware/opencr/README.md`](../../firmware/opencr/README.md)) and
   comment out the `test_motors_with_buttons(...)` line exactly as shown in
   `disable_test_drive.patch`.
4. **Open our sketch**:
   `firmware/opencr/turtlebot3_burger_custom/turtlebot3_burger_custom.ino`
5. **Select** Tools → Board → **OpenCR Board**, and the right **Port**
   (`/dev/ttyACM0` on Linux), then click **Upload**.

<!-- SCREENSHOT SLOT: Arduino IDE with Board=OpenCR + Port selected, ready to Upload.
     Save as assets/opencr-images/arduino-board-port.png and uncomment:
![Arduino IDE board + port selection](../../assets/opencr-images/arduino-board-port.png) -->

## Check it worked

With the robot base running on the Pi (`ros2 launch turtlebot3_bringup
robot.launch.py`), from another terminal:

```bash
ros2 topic echo /sensor_state
```

Press **SW1** then **SW2** — the `button` field in the message should change
(1 for SW1, 2 for SW2). **The robot must NOT move.** If it still drives itself,
the library edit didn't take effect — re-check you edited the exact file the
board package compiles (see the path note in the firmware README), not a stray
copy.

## Wiring the servo dispenser (Pi GPIO, not OpenCR)

Note the supply-box **dispenser servo does not connect to OpenCR** — it goes
straight to the **Pi's GPIO** (covered in [Chapter 6](06-run-mission.md) and
the [bringup README](../../src/ttb3_bringup/README.md)). OpenCR only handles the
drive motors and standard TurtleBot3 sensors.

## Troubleshooting

- **No `/dev/ttyACM0`**: check the USB cable, and that OpenCR has power. `ls
  /dev/ttyACM*` on the Pi.
- **Permission denied on the port** (when flashing from a laptop): add yourself
  to the `dialout` group (`sudo usermod -aG dialout $USER`, then re-login), or
  use the OpenCR reset/boot buttons per the e-Manual.
- **Upload fails partway**: press the OpenCR's **PUSH SW** reset sequence from
  the e-Manual, then retry.

---
← [6. Running the real mission](06-run-mission.md) | [Back to index](00-index.md) | Next: [8. Foxglove →](08-foxglove.md)
