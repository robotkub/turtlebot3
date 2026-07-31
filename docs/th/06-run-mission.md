← [5. เข้าใจ Vision](05-vision.md) | [กลับสารบัญ](00-index.md)

# 6. รัน Mission จริง

## debug.launch.py vs competition.launch.py

| | debug.launch.py | competition.launch.py |
|---|---|---|
| ใช้ตอน | ซ้อม/tune/debug | แข่งจริงเท่านั้น |
| ส่งภาพกล้องให้แล็ปท็อป? | ได้ (compressed) | ไม่ -- ปิดหมด |
| Foxglove/RViz2? | เปิดได้ | ไม่เปิด |
| เครือข่าย | สาย Ethernet, static IP | WiFi อย่างเดียว (ROS_DOMAIN_ID ต้องไม่ซ้ำใคร) |

**ห้ามซ้อมด้วยตัวแข่งจริง ห้ามแข่งด้วยตัว debug** -- เหตุผลคือการส่งภาพกิน
bandwidth WiFi ที่หุ่นต้องใช้ขับเอง ถ้าหลุดกลางทางหุ่นอาจ freeze ต้อง restart
(เสียแต้ม bonus)

## ซ้อม/ทดสอบวันนี้ (ยังไม่ได้ต่อ OpenCR/กล้องจริง)

ถ้ายังไม่ได้ประกอบฮาร์ดแวร์ครบ ทดสอบซอฟต์แวร์อย่างเดียวได้:

```bash
ros2 launch ttb3_bringup debug.launch.py with_robot_base:=false with_camera:=false
```

จะได้ Nav2 + mission node ทั้ง 5 ตัว (dispenser เป็น mock) + Foxglove bridge
ขึ้นมาครบ ทดสอบว่าทุกอย่าง wiring ถูกก่อนประกอบหุ่นจริง

## ต่อฮาร์ดแวร์ครบแล้ว รันจริง

```bash
# ซ้อม/tune
ros2 launch ttb3_bringup debug.launch.py

# แข่งจริง
ros2 launch ttb3_bringup competition.launch.py
```

argument อื่นที่ปรับได้ (map, params_file, use_mock_hardware ฯลฯ) ดูตาราง
เต็มได้ที่ [`../../src/ttb3_bringup/README.md`](../../src/ttb3_bringup/README.md)

## เปิด Foxglove ดูหุ่น

1. **บน Pi**: bridge เปิดเองอัตโนมัติตอนรัน `debug.launch.py` (หรือรันมือ: `foxglove_start`)
2. **บนแล็ปท็อป/มือถือ**: เปิด <https://app.foxglove.dev> (หรือแอปเดสก์ท็อป) ->
   "Open connection" -> **Foxglove WebSocket** -> `ws://<PI_IP>:8765`
   (หา IP ของ Pi ด้วย `hostname -I` บน Pi)
3. **Import layout**: Layout panel -> Import from file ->
   `src/ttb3_bringup/config/foxglove_layout.json` -- จะได้ 3D view (map/lidar/tf),
   ภาพกล้อง, panel ของ tag/victim/mission status/ปุ่ม พร้อม teleop ในหน้าเดียว

ใช้ Foxglove **หรือ** RViz2 (ผ่านสาย Ethernet) อย่างใดอย่างหนึ่งพอ อย่าเปิดพร้อมกัน
เพราะกิน bandwidth ซ้ำซ้อนโดยไม่ได้อะไรเพิ่ม และ **ห้ามเปิดทั้งคู่ตอนแข่งจริง**
(ดูตารางด้านบน)

## Checklist ก่อนวันแข่ง

- [ ] `ROS_DOMAIN_ID` เปลี่ยนเป็นเลขไม่ซ้ำใครแล้ว (ดู [บท 2](02-install.md) หัวข้อ ROS_DOMAIN_ID)
- [ ] มีแผนที่สนามจริงที่ save ไว้แล้ว (`maps/arena_v1.yaml`) ไม่ใช่ placeholder
- [ ] `search_waypoints`/`start_x,y,yaw` ใน `config/mission_params.yaml` ตรงกับสนามจริง
- [ ] tune สีของ victim sign จริงแล้ว (`config/victim_color.yaml`)
- [ ] วัดขนาด AprilTag จริงแล้วใส่ใน `config/tags_36h11.yaml`
- [ ] ตัดสินใจ+ต่อดิสเพนเซอร์จริงแล้ว ปิด `use_mock_hardware`
- [ ] ทดสอบปุ่ม SW1 (reset pose) / SW2 (e-stop) กับฮาร์ดแวร์จริงแล้ว
- [ ] รัน `competition.launch.py` ทดสอบเต็มรอบอย่างน้อย 1 ครั้งก่อนแข่งจริง

ครบทุกข้อ พร้อมแข่งแล้วครับ! กลับไปดูสารบัญได้ที่ [`00-index.md`](00-index.md)

---
← [5. เข้าใจ Vision](05-vision.md) | [กลับสารบัญ](00-index.md)
