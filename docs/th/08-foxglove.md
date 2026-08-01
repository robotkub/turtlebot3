← [7. รัน Mission จริง](07-run-mission.md) | [กลับสารบัญ](00-index.md)

# 8. Foxglove -- ดูหุ่นทำงาน

Foxglove คือ visualizer ที่รันใน **เว็บบราวเซอร์ปกติ** (หรือแอปเดสก์ท็อป) ใช้ดูสิ่งที่หุ่น
เห็น -- แผนที่, lidar, ภาพกล้อง, สถานะ mission -- จากแล็ปท็อปหรือแม้แต่มือถือ โดยเครื่องนั้น
ไม่ต้องลง ROS2

เป็นเครื่องมือ **โหมด debug เท่านั้น** ห้ามเปิดตอนแข่งจริง (กิน WiFi ที่แชร์กัน -- ดู
[บท 7](07-run-mission.md))

## เปิด bridge (บน Pi)

"bridge" คือตัวที่รันบน Pi ให้ Foxglove ต่อเข้า ROS ได้

- เปิด **อัตโนมัติ** พร้อม `ros2 launch ttb3_bringup debug.launch.py`
- หรือเปิดเดี่ยวๆ เมื่อไหร่ก็ได้: `foxglove_start` (alias ที่ install script ใส่ให้ใน `~/.bashrc`)

ฟังที่ port **8765**

## Connect แบบคลิกเดียว (ไม่ต้องผ่าน dialog)

Foxglove เปิด WebSocket connection ตรงจาก URL ได้เลย -- ข้ามขั้นตอน **Open
connection → Foxglove WebSocket → พิมพ์ address** ทุกครั้ง แค่ bookmark ลิงก์พวกนี้ไว้:

| สถานการณ์ | Address | ลิงก์คลิกเดียว |
|---|---|---|
| ต่อหุ่นตรงๆ (`foxglove_bridge` โหมด debug/competition รันบน Pi) | `ws://192.168.1.127:8765` | <https://app.foxglove.dev/view?ds=foxglove-websocket&ds.url=ws%3A%2F%2F192.168.1.127%3A8765> |
| Docker container บนแล็ปท็อป (mapping/Nav2 debug, [บท 9](09-compute-pc.md)) | `ws://localhost:8765` | <https://app.foxglove.dev/view?ds=foxglove-websocket&ds.url=ws%3A%2F%2Flocalhost%3A8765> |

`192.168.1.127` คือ IP ปัจจุบันของหุ่นตัวนี้ -- ถ้า IP เปลี่ยน (ย้ายเน็ตเวิร์ก, DHCP
จ่ายใหม่) เช็คใหม่ด้วย `hostname -I` บน Pi แล้วแก้ IP ในลิงก์ (และในตารางนี้) layout
ล่าสุดที่เปิดค้างไว้จะโหลดขึ้นมาอัตโนมัติ -- ดูหัวข้อถัดไปเพื่อตั้ง layout เฉพาะแต่ละงานไว้ครั้งเดียว
แล้วมันจะติดไปเรื่อยๆ

แล็ปท็อปกับ Pi ต้องอยู่เน็ตเวิร์กเดียวกันและ `ROS_DOMAIN_ID` ตรงกัน (ดู [บท 2](02-install.md))

<!-- SCREENSHOT SLOT: หน้าต่าง "Open connection -> Foxglove WebSocket -> ws://..."
     เซฟเป็น assets/foxglove-images/connect-dialog.png แล้ว uncomment:
![หน้าต่าง connect ของ Foxglove](../../assets/foxglove-images/connect-dialog.png) -->

## Import layout สำเร็จรูป

แทนที่จะสร้าง panel เอง import อันใดอันหนึ่งจากสามแบบที่เตรียมไว้ (คนละอันสำหรับคนละงาน)
**แถบบน → เมนู Layout → Import from file…** แล้วเลือก:

| ไฟล์ | ใช้ตอนไหน | Panel |
|---|---|---|
| [`foxglove_layout.json`](../../src/ttb3_bringup/config/foxglove_layout.json) | รัน `debug.launch.py` / `competition.launch.py` ([บท 7](07-run-mission.md)) | 3D (map/scan/tf) + ภาพกล้อง + `/tag_detections`, `/victim_detections`, `/mission_status`, `/sensor_state` + Teleop |
| [`foxglove_layout_mapping.json`](../../src/ttb3_bringup/config/foxglove_layout_mapping.json) | สร้างแผนที่ด้วย Cartographer ([บท 5](05-navigation.md), [บท 9](09-compute-pc.md)) | 3D เห็นแผนที่กำลังโต (`/map`, `/scan`, submaps, trajectory) + Teleop |
| [`foxglove_layout_nav.json`](../../src/ttb3_bringup/config/foxglove_layout_nav.json) | จูน Nav2 (AMCL localization, costmap, วางแผนเส้นทาง) | 3D (map, costmap, เส้นทางที่วางแผน, AMCL particle cloud) + `/amcl_pose` + ปุ่ม "2D Pose Estimate" + Teleop -- เหมือน RViz default ของ `nav2_bringup` แต่ย้ายมาอยู่ใน Foxglove |

คัดลอกไฟล์ `.json` ไปแล็ปท็อปก่อน หรือเปิด repo บนเครื่องนั้น import แล้วมันจะติดอยู่กับ
account Foxglove ของคุณ (หรือ org ของทีมถ้า sign in ไว้) แล้วเป็น layout ที่ใช้ต่อเนื่องเวลาเปิด
ผ่านลิงก์คลิกเดียวด้านบน -- ไม่ต้อง import ซ้ำทุกครั้ง

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
← [7. รัน Mission จริง](07-run-mission.md) | [กลับสารบัญ](00-index.md)
