← [Back to index](00-index.md) | Next: [2. Installing the software →](02-install.md)

# 1. What You Need + Flashing the SD Card + WiFi Setup

## Equipment checklist

**The robot (TurtleBot3 Burger)**
- Raspberry Pi (SBC) + a micro SD card (32GB+, class 10 or faster recommended)
- OpenCR board
- 2x DYNAMIXEL motors (left/right wheel)
- Lidar -- this project uses **LDS-01** (if your team's unit is a different model, see the note in [Chapter 2](02-install.md))
- USB webcam
- Battery + USB power cable for the Pi
- Dispenser mechanism (drops the supply boxes) -- wiring isn't decided yet, see the checklist in `src/ttb3_bringup/README.md` and confirm with the team before wiring anything

**Also needed**
- An SD card reader for your laptop
- An Ethernet cable (used in debug mode -- see [Chapter 6](06-run-mission.md))
- A WiFi access point both the Pi and your laptop can reach
- A laptop (for the ROS2 desktop install, RViz2, Foxglove)

## Flashing the SD card

Follow ROBOTIS's official guide step by step:
**<https://emanual.robotis.com/docs/en/platform/turtlebot3/sbc_setup/#sbc-setup>**

Quick summary (the official guide has more detail if you get stuck):

1. Download **Raspberry Pi Imager** on your laptop: <https://www.raspberrypi.com/software/>
2. Insert the SD card into the reader
3. Open Raspberry Pi Imager and choose:
   - **Operating System**: Ubuntu Server 22.04 LTS (64-bit) -- must be 22.04 to match ROS2 Humble
   - **Storage**: the SD card you inserted (double-check you picked the right one, so you don't accidentally format another disk)

## Pre-configure WiFi + SSH before flashing (important -- means no monitor/keyboard needed on the Pi at all)

Before hitting "Write" in Raspberry Pi Imager, click the **gear icon (⚙️)** or
press `Ctrl+Shift+X` to open "Edit Settings" and pre-configure:

- **Set hostname**: give the Pi a name (e.g. `turtlebot3`) so you can reach it at `turtlebot3.local` instead of remembering an IP
- **Enable SSH**: turn it on, choose "Use password authentication", and set the username/password your team agreed on
- **Configure wireless LAN**: enter the SSID + password of the WiFi you'll use
- **Set locale settings**: set the correct timezone (Asia/Bangkok)

Click Save, then **Write** to flash the card -- these settings get baked
straight into the image. Once you put the card in the Pi and power it on for
the first time, it connects to WiFi and has SSH ready on its own. No
monitor/keyboard/mouse needed on the Pi at all.

## First login

Wait for the Pi to finish booting (LED blinks for ~1-2 minutes then settles), then find its IP:

```bash
ping turtlebot3.local   # if you set a hostname when flashing
# or check your router's admin page for connected devices
```

Then SSH in with the username/password you set during flashing:

```bash
ssh <username>@<pi-ip-or-hostname>
```

Once you're in, do a quick sanity check before moving on:

```bash
lsb_release -a       # should show Ubuntu 22.04
uname -m              # should show aarch64 (arm64)
```

All good? Move on to [Chapter 2: Installing the software](02-install.md).

---
← [Back to index](00-index.md) | Next: [2. Installing the software →](02-install.md)
