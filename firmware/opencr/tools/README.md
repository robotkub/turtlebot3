# Vendored ROBOTIS OpenCR upload tools

`opencr_ld_shell_arm` and `opencr_ld_shell_x86` are ROBOTIS's own firmware
upload/packaging tool, taken from the `opencr_update.tar.bz2` bundle they
publish for flashing prebuilt TurtleBot3 firmware:

<https://github.com/ROBOTIS-GIT/OpenCR-Binaries/raw/master/turtlebot3/ROS2/latest/opencr_update.tar.bz2>

Same tool, two architectures:

- `opencr_ld_shell_arm` -- runs the actual serial upload on the Pi
  (`flash_opencr.sh` uses this one). ARM ELF binary, works natively on
  Raspberry Pi's aarch64/armhf.
- `opencr_ld_shell_x86` -- used by `build_firmware.sh` (in an x86_64 build
  container) to wrap a freshly-compiled `.bin` into the `.opencr` format this
  tool expects, via its `make <bin> <name> <version>` mode.

Vendored (rather than downloaded at flash time) so flashing a robot never
depends on GitHub being reachable. ROBOTIS ships this binary for exactly this
kind of redistribution -- it's the same tool their own e-Manual instructs
teams to download and run directly on a Raspberry Pi.
