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
- A WiFi access point both the Pi and your laptop can reach
- A laptop (for Foxglove visualization — **no native ROS2 install needed**, everything runs in Docker)

## Flashing the SD card

Follow ROBOTIS's official guide step by step:
**<https://emanual.robotis.com/docs/en/platform/turtlebot3/sbc_setup/#sbc-setup>**

Quick summary (the official guide has more detail if you get stuck):

1. Download **Raspberry Pi Imager** on your laptop: <https://www.raspberrypi.com/software/>
2. Insert the SD card into the reader
3. Open Raspberry Pi Imager -- you'll see three columns to fill in: **Raspberry Pi Device**, **Operating System**, **Storage**

   ![Raspberry Pi Imager main screen, three columns to fill in](../../assets/rasberrypi-images/raspberrypi-image-select-pi-version.png)

4. Click **Raspberry Pi Device** and pick the model you actually have (this project's robot uses a **Raspberry Pi 3**):

   ![Choosing the Raspberry Pi Device -- Raspberry Pi 3 selected](../../assets/rasberrypi-images/raspberrypi-image-select-pi-version-model.png)

5. Click **Operating System**:

   ![Clicking the Operating System column](../../assets/rasberrypi-images/raspberrypi-image-select-pi-os.png)

   Choose **Other general-purpose OS** (not the default Raspberry Pi OS -- we need Ubuntu):

   ![Selecting "Other general-purpose OS"](../../assets/rasberrypi-images/raspberrypi-image-select-pi-os-other-general.png)

   Then **Ubuntu**:

   ![Selecting "Ubuntu"](../../assets/rasberrypi-images/raspberrypi-image-select-pi-os-ubuntu.png)

   Then **Ubuntu Server 22.04.5 LTS (64-bit)** -- must be 22.04 to match ROS2 Humble, don't pick a newer or older version:

   ![Selecting Ubuntu Server 22.04.5 LTS (64-bit)](../../assets/rasberrypi-images/raspberrypi-image-select-pi-os-ubuntu-22.04.png)

6. Click **Storage** and pick the SD card you inserted (double-check you picked the right one, so you don't accidentally format another disk):

   ![Choosing the SD card as Storage](../../assets/rasberrypi-images/raspberrypi-image-select-pi-sd-card.png)

7. All three columns filled in -- click **NEXT**:

   ![All three columns filled in, clicking Next](../../assets/rasberrypi-images/raspberrypi-image-select-pi-next.png)

## Pre-configure WiFi + SSH before flashing (important -- means no monitor/keyboard needed on the Pi at all)

After clicking Next, Imager asks if you want to apply OS customisation
settings -- choose **Edit Settings** (or click the **gear icon (⚙️)** /
press `Ctrl+Shift+X` beforehand) and pre-configure, on the **GENERAL** tab:

- **Set hostname**: give the Pi a name (e.g. `turtlebot3`) so you can reach it at `turtlebot3.local` instead of remembering an IP
- **Set username and password**: the username/password your team agreed on
- **Configure wireless LAN**: enter the SSID + password of the WiFi you'll use, and the wireless LAN country (`TH`)
- **Set locale settings**: set the correct timezone (`Asia/Bangkok`)

![OS Customisation -- General tab: hostname, username/password, WiFi, locale](../../assets/rasberrypi-images/raspberrypi-image-config-user.png)

Then switch to the **SERVICES** tab and turn on SSH:

- **Enable SSH**: turn it on, choose **Use password authentication**

![OS Customisation -- Services tab: Enable SSH with password authentication](../../assets/rasberrypi-images/raspberrypi-image-config-user-ssh.png)

Click Save, then **Write** to flash the card -- these settings get baked
straight into the image. Once you put the card in the Pi and power it on for
the first time, it connects to WiFi and has SSH ready on its own. No
monitor/keyboard/mouse needed on the Pi at all.

> Whatever hostname/username/password/WiFi credentials you set here, keep
> them out of anything you commit to a public repo (don't paste real
> credentials into docs, screenshots, or commit messages).

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

On this team's robot:

```bash
ssh skuba@skuba.local
```

Don't drop the `skuba@` -- `ssh skuba.local` logs in as *your laptop's*
username and denies the password every time.

Once you're in, do a quick sanity check before moving on:

```bash
lsb_release -a       # should show Ubuntu 22.04
uname -m              # should show aarch64 (arm64)
```

All good? Move on to [Chapter 2: Installing the software](02-install.md).

---
← [Back to index](00-index.md) | Next: [2. Installing the software →](02-install.md)
