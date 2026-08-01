# OpenCR custom firmware

The OpenCR board is the robot's "reflexes": it spins the wheel motors, reads
the IMU/encoders/buttons, and reports everything to the Pi over USB. It runs
**Arduino/C++ firmware**, flashed once and rarely changed.

We run a lightly customized version of ROBOTIS's standard TurtleBot3 firmware.

## Why customize at all?

Stock firmware hard-codes a **test-drive on the push buttons** (for checking
motors during assembly): pressing **SW1 drives the robot forward ~0.3 m**, and
**SW2 spins it 180°**. Our mission uses those same two buttons as controls:

| Button | RobotKub meaning (handled in ROS) |
|---|---|
| SW1 | START the mission (in IDLE) / RESUME (after e-stop) |
| SW2 | E-STOP (stop now, cancel navigation) |

If we kept stock firmware, the robot would lurch forward or spin every time an
operator pressed a mission button — unacceptable and dangerous. So we disable
the built-in test-drive. After the change, the buttons **only report their
state** on the `/sensor_state` topic, and `ttb3_mission/button_handler` decides
what each press means.

## What's in this folder

- **`flash_opencr.sh`** — the command students/teammates actually run, on the
  Pi. It just uploads the **already-compiled** `prebuilt/turtlebot3_burger_custom.opencr`
  over serial. No arduino-cli, no compiler, no internet needed on the Pi --
  it's a plain serial file transfer, so it works on the Pi's ARM CPU with zero
  setup.
- **`build_firmware.sh`** — **maintainer-only**. Recompiles the sketch (with
  `disable_test_drive.patch` applied) and regenerates `prebuilt/turtlebot3_burger_custom.opencr`.
  Only needed when the sketch or patch changes -- see "Rebuilding the firmware"
  below for why this can't run on the Pi either.
- `prebuilt/turtlebot3_burger_custom.opencr` — the compiled, ready-to-flash
  firmware (committed to the repo so nobody needs to compile anything to flash
  a robot). `prebuilt/BUILD_INFO.txt` records when/how it was built.
- `tools/opencr_ld_shell_arm`, `tools/opencr_ld_shell_x86` — ROBOTIS's own
  firmware upload/packaging tool, vendored from their `OpenCR-Binaries`
  releases (see `tools/README.md`) so flashing doesn't depend on GitHub being
  reachable at flash time.
- `turtlebot3_burger_custom/turtlebot3_burger_custom.ino` — the sketch. It's the
  same thin wrapper as ROBOTIS's `turtlebot3_burger` example; the actual change
  is in the library (next item).
- `disable_test_drive.patch` — the exact one-line change `build_firmware.sh`
  applies to the `turtlebot3_ros2` library file `turtlebot3.cpp` before
  compiling; this documents what it does.

## Quick flash (recommended) -- one command on the Pi

With OpenCR connected by USB:

```bash
cd ~/turtlebot3_ws/firmware/opencr
./flash_opencr.sh                # auto-detects the port
# ./flash_opencr.sh /dev/ttyACM0 # or name it
```

This just uploads the prebuilt firmware -- no compiling, no arduino-cli, no
network access needed. The rest of this file (including "Rebuilding the
firmware" and the manual Arduino-IDE path) is maintainer-level detail for when
the firmware itself needs to change.

## Rebuilding the firmware (maintainers only)

`prebuilt/turtlebot3_burger_custom.opencr` needs a rebuild whenever
`turtlebot3_burger_custom.ino` or `disable_test_drive.patch` changes. This
can't be done on the Pi or on an Apple Silicon Mac: the OpenCR board
package's compiler (`opencr_gcc` 5.4.0-2016q2) only ships prebuilt binaries
for `x86_64-pc-linux-gnu`, `i686-linux-gnu`, Windows, and old 32-bit Intel
macOS -- there is no `aarch64` build.

`build_firmware.sh` works around this by compiling inside an emulated x86_64
Docker container (works via Docker Desktop's Rosetta/QEMU amd64 emulation on
Apple Silicon, natively on any x86_64 host):

```bash
cd ~/turtlebot3_ws/firmware/opencr   # or wherever you cloned the repo
./build_firmware.sh
git add prebuilt/turtlebot3_burger_custom.opencr prebuilt/BUILD_INFO.txt
git commit -m "firmware: rebuild after <describe the sketch/patch change>"
```

The script also works around a second gotcha: the `gcc-arm-none-eabi`
toolchain the compiler needs lives on an old Launchpad mirror that's
throttled to ~14 KB/s and doesn't support resuming (the 88 MB file can take
90+ minutes and any dropped connection means starting over). The script
fetches the identical, checksum-verified bytes from an archive.org cache
instead, which is orders of magnitude faster, and falls back to the original
Launchpad URL only if that ever goes away.

## One-time toolchain setup (Arduino IDE)

Follow ROBOTIS's OpenCR setup guide for the authoritative steps and screenshots:
<https://emanual.robotis.com/docs/en/platform/turtlebot3/opencr_setup/>

Summary:
1. Install the **Arduino IDE** (1.8.x or 2.x): <https://www.arduino.cc/en/software>
2. Add the OpenCR board manager URL: **File → Preferences → Additional Boards
   Manager URLs**, add
   `https://raw.githubusercontent.com/ROBOTIS-GIT/OpenCR/master/arduino/opencr_release/package_opencr_index.json`
3. **Tools → Board → Boards Manager**, search **OpenCR**, install it.
4. Select **Tools → Board → OpenCR → OpenCR Board**, and the right **Port**
   (the OpenCR shows up as `/dev/ttyACM0` on Linux once plugged in via USB).

The OpenCR board package ships the `turtlebot3_ros2` library that contains
`TurtleBot3Core` — that's the library we patch.

## Where the library lives

The `turtlebot3.cpp` you edit is inside the installed OpenCR package:

- **Linux**: `~/.arduino15/packages/OpenCR/hardware/OpenCR/<version>/libraries/turtlebot3_ros2/src/turtlebot3/turtlebot3.cpp`
- **macOS**: `~/Library/Arduino15/packages/OpenCR/hardware/OpenCR/<version>/libraries/turtlebot3_ros2/src/turtlebot3/turtlebot3.cpp`
- **Windows**: `C:\Users\<you>\AppData\Local\Arduino15\packages\OpenCR\hardware\OpenCR\<version>\libraries\turtlebot3_ros2\src\turtlebot3\turtlebot3.cpp`

(If you can't find it, search your home folder for `turtlebot3.cpp`.)

## Apply the change and flash

1. Open `disable_test_drive.patch` and make that one edit in `turtlebot3.cpp`
   (comment out the `test_motors_with_buttons(...)` call). Save.
2. In Arduino IDE, open `firmware/opencr/turtlebot3_burger_custom/turtlebot3_burger_custom.ino`.
3. Confirm **Board = OpenCR Board** and the correct **Port** are selected.
4. Click **Upload**. Wait for "jump_to_fw ..." / done in the console.
5. Sanity check from the Pi once the robot base is up
   (`ros2 launch turtlebot3_bringup robot.launch.py`):
   ```bash
   ros2 topic echo /sensor_state    # press SW1/SW2 -> the `button` field changes
   ```
   The robot should NOT move when you press the buttons. If it still drives,
   the library edit didn't take — re-check you edited the file the board
   package actually compiles (the path above), not a different copy.

## Keeping it in sync

We deliberately keep only the sketch + a documented patch here rather than
vendoring ROBOTIS's whole library — the library is large and updates with the
board package. When you update the OpenCR board package, re-apply the one-line
patch (it's tiny and unlikely to move).
