← [7. OpenCR + Custom Firmware](07-opencr.md) | [กลับสารบัญ](00-index.md)

# 8. Foxglove -- ดูหุ่นทำงาน

Foxglove คือ visualizer ที่รันใน **เว็บบราวเซอร์ปกติ** (หรือแอปเดสก์ท็อป) ใช้ดูสิ่งที่หุ่น
เห็น -- แผนที่, lidar, ภาพกล้อง, สถานะ mission -- จากแล็ปท็อปหรือแม้แต่มือถือ โดยเครื่องนั้น
ไม่ต้องลง ROS2

เป็นเครื่องมือ **โหมด debug เท่านั้น** ห้ามเปิดตอนแข่งจริง (กิน WiFi ที่แชร์กัน -- ดู
[บท 6](06-run-mission.md))

## เปิด bridge (บน Pi)

"bridge" คือตัวที่รันบน Pi ให้ Foxglove ต่อเข้า ROS ได้

- เปิด **อัตโนมัติ** พร้อม `ros2 launch ttb3_bringup debug.launch.py`
- หรือเปิดเดี่ยวๆ เมื่อไหร่ก็ได้: `foxglove_start` (alias ที่ install script ใส่ให้ใน `~/.bashrc`)

ฟังที่ port **8765**

## Connect (บนแล็ปท็อป / มือถือ)

1. เปิด **<https://app.foxglove.dev>** ในบราวเซอร์ หรือลงแอปเดสก์ท็อป Foxglove
2. กด **Open connection**
3. เลือก **Foxglove WebSocket**
4. ใส่ `ws://<PI_IP>:8765` -- หา IP ของ Pi ด้วย `hostname -I` บน Pi
   (เช่น `ws://192.168.1.127:8765`)

แล็ปท็อปกับ Pi ต้องอยู่เน็ตเวิร์กเดียวกันและ `ROS_DOMAIN_ID` ตรงกัน (ดู [บท 2](02-install.md))

<!-- SCREENSHOT SLOT: หน้าต่าง "Open connection -> Foxglove WebSocket -> ws://..."
     เซฟเป็น assets/foxglove-images/connect-dialog.png แล้ว uncomment:
![หน้าต่าง connect ของ Foxglove](../../assets/foxglove-images/connect-dialog.png) -->

## Import layout สำเร็จรูป

แทนที่จะสร้าง panel เอง import layout ที่เราเตรียมไว้:

1. แถบบน → เมนู **Layout** → **Import from file…**
2. เลือก
   [`src/ttb3_bringup/config/foxglove_layout.json`](../../src/ttb3_bringup/config/foxglove_layout.json)
   (คัดลอกไปแล็ปท็อปก่อน หรือเปิด repo บนเครื่องนั้น)

จะได้ในหน้าเดียว:

| Panel | แสดง |
|---|---|
| **3D** | แผนที่, lidar `/scan` สด, และ TF frame ของหุ่น |
| **Image** | ภาพกล้อง (`/image_raw/compressed`) |
| **Raw Messages** ×4 | `/tag_detections`, `/victim_detections`, `/mission_status`, `/sensor_state` |
| **Teleop** | ขับหุ่นด้วยการ publish `/cmd_vel` |

<!-- SCREENSHOT SLOT: dashboard ที่ import แล้ว มี panel ครบ
     เซฟเป็น assets/foxglove-images/dashboard.png แล้ว uncomment:
![Foxglove dashboard](../../assets/foxglove-images/dashboard.png) -->

## ดูอะไรบ้าง

- **`/mission_status`** -- panel ที่มีประโยชน์ที่สุด แสดง state machine สดๆ: `IDLE → INIT →
  SEARCH → APPROACH_VICTIM → DISPENSE → RETURN_HOME → DONE` พร้อม `boxes_dispensed`,
  `boxes_target`, `estop_active` ถ้าหุ่นไม่ทำตามที่คาด ดูตรงนี้ก่อน
- **`/sensor_state`** -- ฟิลด์ `button` เปลี่ยนเมื่อกด SW1/SW2 (เช็คปุ่ม + firmware เร็วๆ)
- **panel 3D** -- ถ้าหุ่น "หลง" (nav เพี้ยน) เช็คว่าเส้น lidar ตรงกับกำแพงในแผนที่ไหม ถ้าไม่ตรง
  แปลว่า localize เพี้ยน (เรียก `reset_to_start` ด้านล่าง)

## เรียก service จาก Foxglove (start, reset, save start pose)

เพิ่ม panel **Service Call** ("+" เพิ่ม panel → *Service Call*) เพื่อสั่งหุ่นโดยไม่ต้องแตะ terminal:

| Service | Type | ทำอะไร |
|---|---|---|
| `/reset_to_start` | `ttb3_msgs/srv/ResetToStart` | re-localize กลับ START pose (เก็บความคืบหน้าไว้) |
| `/save_start_pose` | `ttb3_msgs/srv/SaveStartPose` | จับตำแหน่ง *ปัจจุบัน* ของหุ่นเป็น START ใหม่ (ขับไปตรงนั้นก่อน) |

จะ **start mission** โดยไม่ใช้ปุ่มจริงก็ได้ ด้วยการ publish ข้อความเปล่าไปที่ **`/mission_start`**
(`std_msgs/msg/Empty`) จาก panel Publish -- สะดวกตอน bench-test

## ความปลอดภัยของ Teleop

panel Teleop publish `/cmd_vel` ตรงๆ ซึ่งจะ **ตีกับ `/cmd_vel` ของ mission** ถ้า mission
กำลังรัน ให้ teleop เฉพาะตอน mission อยู่ `IDLE` หรือ `DONE` (หรือหลัง e-stop) และพร้อม
กด e-stop เสมอ ใช้ Foxglove **หรือ** RViz2 อย่างใดอย่างหนึ่ง อย่าเปิดพร้อมกัน

---
← [7. OpenCR + Custom Firmware](07-opencr.md) | [กลับสารบัญ](00-index.md)
