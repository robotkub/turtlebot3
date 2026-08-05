← [8. Foxglove](08-foxglove.md) | [กลับหน้าสารบัญ](00-index.md)

# 9. ย้ายภาระประมวลผลไปแล็ปท็อป (Docker — ทางเดียวของแล็ปท็อป)

Raspberry Pi 3 B+ (quad-core ARM Cortex-A53 @ 1.4 GHz, 1 GB RAM) บนหุ่นยนต์มีทรัพยากรจำกัด แม้จะคุมมอเตอร์ อ่านเซนเซอร์ รัน perception และภารกิจหลักได้ดี แต่การรัน SLAM (slam_toolbox) และ Nav2 localization/planning หนักๆ ไปพร้อมกันขณะสร้างแผนที่หรือทดสอบจูนระบบอาจสร้างภาระให้เครื่องมากเกินไป

สมาชิกทีมที่ใช้แล็ปท็อปย้ายการประมวลผลนี้มารันใน Docker container — **ไม่ต้องลง
ROS 2 บนเครื่องแล็ปท็อปเลย** Docker ทำให้ workflow ไม่ขึ้นกับ OS: คำสั่งเดียวกัน
ใช้ได้บน macOS, Windows และ Linux ทำให้ไม่ต้องสู้กับ apt หรือดูแล ROS2 install
บนเครื่องของตัวเอง

> [!IMPORTANT]
> **สำหรับโหมด Debug/Testing เท่านั้น!**
> การย้ายการประมวลผลนี้ใช้สำหรับ **การสร้างแผนที่ (mapping) การจูน และการทดสอบ debug เท่านั้น** ในวันแข่งจริง `competition.launch.py` จะรันบน Raspberry Pi แบบ standalone เต็มรูปแบบ โดยไม่ต้องพึ่งพาแล็ปท็อป (ตรงตามข้อกำหนด SRS R10 / N3/N4 เรื่องแบนด์วิดธ์ WiFi ในสนามแข่ง)

---

## สถาปัตยกรรมระบบ (Architecture)

- **อุปกรณ์กายภาพ**: มี 2 เครื่อง คือ Raspberry Pi (บนหุ่น) + แล็ปท็อป
- **สภาพแวดล้อมบนแล็ปท็อป**: รัน ROS 2 Humble ผ่าน Docker container (`ttb3-compute`) **ไม่ต้องติดตั้ง ROS 2 แบบ bare-metal บนแล็ปท็อปเลย**
- **การเชื่อมต่อเครือข่าย**: ใช้ **Zenoh** (`rmw_zenoh_cpp`) ไม่ใช่ CycloneDDS Zenoh router รันบน Pi; container บนแล็ปท็อปเชื่อมต่อผ่าน **unicast TCP** (`ROBOT_IP:7447`) ไม่ใช่ multicast discovery
  > [!IMPORTANT]
  > เราเปลี่ยนมาจาก CycloneDDS เพราะ UDP multicast discovery ของมันไม่ทำงานผ่าน Docker Desktop บน Mac/Windows — `network_mode: host` ที่นั่นไม่ใช่ host network จริง (Docker Desktop รัน container อยู่ใน VM) ทำให้ multicast ไม่ถึงหุ่นแม้ดูเหมือนจะถึง Zenoh ใช้ unicast connect แบบ explicit แก้ปัญหานี้ได้ ดู `docker/zenoh_client_config.json5.template`
- **การแสดงผล (Visualization)**: ใช้ Foxglove Bridge (`visualize:=true`) ที่ถูกรวมอยู่ใน launch file (เชื่อมต่อ WebSocket ที่ `ws://localhost:8765`) เป็น visualizer ตัวเดียวที่โปรเจกต์นี้ใช้

```mermaid
graph TB
    subgraph Pi["🤖 Raspberry Pi (บนหุ่น)"]
        direction TB
        ZR["zenoh-router.service\n(systemd — auto-start ตอนบูต)"]
        RB["robot.launch.py\n(OpenCR bridge, lidar, กล้อง)"]
        MI["mission_manager\n+ perception nodes"]
        FB["foxglove_bridge\n:8765 (debug mode เท่านั้น)"]
        ZR --- RB
        RB --- MI
        MI --- FB
    end

    subgraph Laptop["💻 แล็ปท็อป (macOS / Windows / Linux)"]
        direction TB
        DC["docker compose run ttb3-compute"]
        MAP["mapping.launch.py\n(slam_toolbox SLAM +\njoy + twist_mux)"]
        NAV["navigation.launch.py\n(Nav2 + AMCL +\njoy + twist_mux)"]
        TP["teleop_keyboard\n(terminal แยก -- ต้องใช้\nTTY จริงของตัวเอง)"]
        FOX["Foxglove Studio\nws://localhost:8765"]
        DC --> MAP
        DC --> NAV
        DC --> TP
        FOX -.- DC
    end

    Pi <-->|"Zenoh unicast TCP\nROBOT_IP:7447\n(WiFi)"| Laptop
    FB -.->|"WebSocket :8765"| FOX
```

---

## การเตรียมระบบครั้งแรก (One-Time Setup)

**ไม่ต้องตั้งค่าอะไรเลย** `./ttb3` อ่าน `ROS_DOMAIN_ID` จาก `.env` ที่ commit
ไว้แล้ว และ resolve ชื่อ `skuba.local` เป็น IPv4 ใหม่ทุกครั้งที่รัน IP เปลี่ยน
ตาม DHCP ก็ไม่พัง สั่ง build image ครั้งเดียวก็จบ:

```bash
./ttb3 build
```

`./src` ถูก **mount** เข้า container และ image build ด้วย `--symlink-install`
ดังนั้น launch file, YAML param และโค้ด Python เป็นแบบสดๆ -- แก้บนเครื่องแล้ว
`./ttb3 nav` รอบถัดไปเห็นเลย ต้อง build ใหม่เฉพาะตอนแก้ interface ของ `ttb3_msgs`,
เพิ่ม entry point ของ node ใหม่ หรือแก้รายการ apt ใน Dockerfile เท่านั้น

คำสั่งนี้คอมไพล์ `ttb3_bringup` ลงใน image ROS 2 Humble headless ที่มี slam_toolbox, Nav2, Foxglove Bridge, TurtleBot3 teleop และ Zenoh

<details>
<summary>รูปแบบ <code>docker compose</code> ดิบๆ สำหรับอ้างอิง</summary>

ต้อง export ตัวแปรทั้งสองใน shell ที่จะรัน `docker compose` ทุกคำสั่ง --
`docker-compose.yml` ต้องใช้ `ROBOT_IP` ตั้งแต่ parse ไฟล์ ดังนั้น `build` ก็ต้อง
มีด้วย ถ้าไม่มีจะ fail ด้วย "required variable ROBOT_IP is missing a value"
แล้ว image จะค้างเป็นตัวเก่าแบบเงียบๆ

`ROBOT_IP` ต้องเป็น **IPv4 แบบตัวเลขเท่านั้น** ห้ามใส่ `skuba.local` เพราะค่านี้
ถูกแทนลงใน `tcp/${ROBOT_IP}:7447` ที่ไม่มีวงเล็บ ซึ่งเขียน IPv6 ที่ชื่อ `.local`
ตอบกลับมาก่อนไม่ได้ ดู IP ด้วย `hostname -I` บน Pi

```bash
export ROS_DOMAIN_ID=42
export ROBOT_IP=<ipv4 ปัจจุบันของ Pi>
docker compose build
```

</details>

---

## ขั้นตอนการทำงานที่ 1: การสร้างแผนที่ (slam_toolbox + Map Autosaver)

1. **บน Raspberry Pi**: สั่งเปิดระบบฐานหุ่นยนต์ (OpenCR bridge & Lidar) Zenoh router รันอัตโนมัติผ่าน systemd ไม่ต้องสั่งเอง:
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **บนแล็ปท็อป**: สั่งรัน slam_toolbox mapping ผ่าน Docker:
   ```bash
   ./ttb3 map
   ```
   จะขึ้นบรรทัดบอกว่าเจอหุ่นที่ไหน (`robot: skuba.local -> 192.168.1.x`) ก่อนเริ่ม
   ถ้า export ตัวแปรเองก็เทียบเท่ากับ:
   ```bash
   docker compose run --rm --service-ports ttb3-compute \
     ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true
   ```

3. **ดูผลลัพธ์และบังคับหุ่น**:
   - เปิด Foxglove Studio (`ws://localhost:8765`) เพื่อดูแผนที่กำลังสร้างแบบ real-time
   - จอยสติ๊ก/เกมแพดเปิดมาให้อัตโนมัติใน `mapping.launch.py` (เฉพาะเครื่อง Linux -- Docker Desktop บน Mac/Windows ไม่ pass-through `/dev/input`) arbitrate ลง `/cmd_vel` ผ่าน `twist_mux`
   - ถ้าจะขับด้วยคีย์บอร์ด ให้รัน `teleop_keyboard` ใน **terminal แยกของตัวเอง** -- มันต้องคุม TTY จริงเพื่ออ่านปุ่มกด และ `ros2 launch` ให้ TTY จริงกับ child process ที่ bundle เข้าไปไม่ได้ (ยืนยันแล้ว: ถ้าลอง bundle จะพังด้วย `termios.error`):
     ```bash
     docker compose run --rm ttb3-compute ros2 run turtlebot3_teleop teleop_keyboard \
       --ros-args -r cmd_vel:=cmd_vel_teleop
     ```
     (`stdin_open: true` / `tty: true` ใน `docker-compose.yml` ส่งปุ่มแป้นพิมพ์ให้ process นี้โดยตรง ถ้าใช้ทั้งคู่ joy priority จะสูงกว่าคีย์บอร์ด)
   - เมื่อสร้างแผนที่เสร็จแล้ว ให้กด `Ctrl-C` ที่เทอร์มินัล mapping ไฟล์แผนที่ (`arena_v1.pgm` และ `arena_v1.yaml`) จะถูกบันทึกลงในโฟลเดอร์ `./maps/` บนเครื่องแล็ปท็อปโดยอัตโนมัติผ่าน volume mount (`./maps:/maps`)

---

## ขั้นตอนการทำงานที่ 2: การทดสอบ Nav2 Standalone & Tuning

สำหรับการทดสอบและจูน Nav2 (AMCL + Path Planner) กับแผนที่ที่บันทึกไว้:

1. **บน Raspberry Pi**: สั่งเปิดระบบฐานหุ่นยนต์ Zenoh router รันอัตโนมัติผ่าน systemd:
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **บนแล็ปท็อป**: สั่งรัน Nav2 standalone ใน Docker:
   ```bash
   ./ttb3 nav
   ```
   หรือรูปแบบดิบๆ ถ้า export ตัวแปรเอง:
   ```bash
   docker compose run --rm --service-ports ttb3-compute \
     ros2 launch ttb3_bringup navigation.launch.py visualize:=true
   ```

3. **แสดงผลและกำหนดจุดเป้าหมาย**:
   - เชื่อมต่อ Foxglove ไปที่ `ws://localhost:8765`
   - กำหนด 2D Pose Estimate และ Nav Goal ผ่าน Foxglove
   - teleop joy ก็ bundle มาใน `navigation.launch.py` ด้วย โดย arbitrate กับ output ของ Nav2 ผ่าน `twist_mux` (priority: joy > คีย์บอร์ด > Nav2) -- คีย์บอร์ดต้องรันแยก terminal เหมือนขั้นตอนที่ 1 -- บังคับหุ่นเองได้ทุกเมื่อเพื่อ override Nav2 เช่นตอนหุ่นติด recovery

---

## ขั้นตอนการทำงานที่ 3: รัน mission ทั้งหมดบนแล็ปท็อป

อันนี้คือของจริง และเป็นเหตุผลที่บทนี้มีอยู่ Pi รันแค่ driver ส่วน Nav2, perception
และ mission state machine รันใน container นี้ทั้งหมด:

1. **บน Pi**: เฉพาะ driver
   ```bash
   ros2 launch ttb3_bringup hardware.launch.py
   ```
   (หรือให้ขึ้นเองตอน boot — `sudo systemctl enable --now ttb3-hardware.service`
   installer เขียน unit นี้ให้แล้วแต่ยังไม่ enable เพราะการที่มอเตอร์มีไฟทันทีที่เปิด Pi
   เป็น default ที่อันตรายตอนที่ยังประกอบหุ่นไม่เสร็จ)

2. **บนแล็ปท็อป**: ทุกอย่างที่ต้องคิด
   ```bash
   ./ttb3 mission
   ```

ทำไมต้องแยก: รันทั้งสแต็กบน Pi 3/4 ตัวเดียวมันตัน ตอนที่ Nav2, apriltag และ
mission node รันพร้อมกัน Pi ยังตอบ ping อยู่แต่ `sshd` ทำ banner exchange ไม่จบ
แล้ว -- คือ login เข้าไปสั่งหยุดยังทำไม่ได้ zenoh เป็นตัวเชื่อม ROS graph ระหว่าง
สองเครื่อง โค้ดเลยไม่ต้องรู้ว่าตัวเองรันอยู่ฝั่งไหน

สิ่งที่ยังทำงานได้เหมือนเดิมหลังแยก:

- **ปุ่มจริงบนหุ่น** `button_handler` อ่าน SW1/SW2 จาก `/sensor_state` ที่ OpenCR
  publish ขึ้น graph ที่ใช้ร่วมกัน
- **ดิสเพนเซอร์** ยังอยู่บน Pi (เพราะขับ servo ผ่าน GPIO) และรับคำสั่งผ่าน
  `/dispense_command` จากที่ไหนก็ได้
- **กล้อง** `hardware.launch.py` publish `/image_raw/compressed` แล้ว
  `mission.launch.py` decompress เป็น `/camera/image_raw` ฝั่งนี้เพื่อป้อน perception
  ภาพ raw ไม่วิ่งข้าม WiFi เลย -- ตามข้อ N3

ข้อแลกเปลี่ยนที่ต้องรู้: WiFi กลายเป็นส่วนหนึ่งของ control loop ของหุ่น ตอนซ้อมไม่มีปัญหา
แต่ตอนแข่งจริงต้องชั่งกับข้อ R10 -- `competition.launch.py` ตั้งใจให้ทุกอย่างอยู่บนหุ่น
เพื่อไม่ให้แล็ปท็อปที่หลุด WiFi พาสมองของ mission หายไปด้วย

---

## ข้อกำหนดสำคัญและการตั้งค่า

- **`ROS_DOMAIN_ID`**: ต้องตรงกันระหว่าง Raspberry Pi และแล็ปท็อป (ค่าเริ่มต้นคือ `42`) `./ttb3` อ่านจาก `.env` ที่ commit ไว้ให้แล้ว ต้อง export เองเฉพาะตอนสั่ง `docker compose` ตรงๆ
- **การหาหุ่น**: `./ttb3` resolve `skuba.local` (avahi/mDNS บน Pi) เป็น IPv4 ใหม่ทุกครั้งที่รัน IP เปลี่ยนตาม DHCP ก็ไม่ต้องแก้อะไรเลย แล้ว zenoh session ของ container ก็เชื่อมต่อไปที่ address นั้นผ่าน unicast TCP
- **`ROBOT_IP`**: ตัวเลือกเสริมสำหรับ override เมื่อเน็ตเวิร์กบล็อก mDNS ต้องเป็น **IPv4 แบบตัวเลขเท่านั้น** — ใส่ชื่อ `.local` จะทำให้ endpoint `tcp/${ROBOT_IP}:7447` ที่ไม่มีวงเล็บพัง เพราะเขียน IPv6 ไม่ได้ ถ้าตั้งค่านี้ `./ttb3` จะขึ้นว่า `robot: pinned …` ลบทิ้งเพื่อกลับไปหาหุ่นด้วยชื่อ
- **DDS Middleware**: ใช้ `rmw_zenoh_cpp` ตรงกันทั้งสองฝ่าย Router รันบน Pi เป็น systemd service (`zenoh-router.service`, ติดตั้งโดย `install-humble-turtlebot3.sh`) เช็คด้วย `systemctl status zenoh-router.service` manual start (`zenoh_router_start`) ยังมีสำหรับ debug
- **Host Volume Mounting**: โฟลเดอร์ `./maps` บนแล็ปท็อปถูกผูกกับ `/maps` ใน container ทำให้แผนที่ที่เซฟได้อยู่บนดิสก์ของเครื่องแล็ปท็อปทันที

---

← [8. Foxglove](08-foxglove.md) | [กลับหน้าสารบัญ](00-index.md)
