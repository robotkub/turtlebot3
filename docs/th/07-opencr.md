← [6. รัน Mission จริง](06-run-mission.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [8. Foxglove →](08-foxglove.md)

# 7. OpenCR + Custom Firmware

## OpenCR คืออะไร

OpenCR คือสมองตัวที่สองของหุ่น -- ไมโครคอนโทรลเลอร์ (เหมือน Arduino ตัวแรงๆ) ในขณะที่
Pi ทำงาน "คิด" (แผนที่, vision, ตัดสินใจ) OpenCR ทำงาน "รีเฟล็กซ์": หมุนมอเตอร์ล้อ
ตามความเร็วที่สั่งเป๊ะๆ อ่าน IMU / encoder / ปุ่ม แล้วรายงานทุกอย่างให้ Pi

- ต่อกับ Pi ผ่าน **USB** (โผล่มาเป็น `/dev/ttyACM0`)
- รัน **firmware Arduino/C++** flash ครั้งเดียว แทบไม่ต้องแก้อีก
- publish `/odom`, `/imu`, `/sensor_state` และ subscribe `/cmd_vel`

## ทำไมต้อง custom firmware

firmware มาตรฐานของ ROBOTIS **ฝัง test-drive ไว้ที่ปุ่ม** (ไว้เช็คมอเตอร์ตอนประกอบ):

- **SW1 → หุ่นวิ่งหน้า ~0.3 ม.**
- **SW2 → หมุน 180°**

แต่ mission เราต้องใช้ 2 ปุ่มนั้นเป็นปุ่มควบคุม:

| ปุ่ม | ความหมาย (ตัดสินใจฝั่ง ROS ไม่ใช่ firmware) |
|---|---|
| **SW1** | **START** เริ่ม mission (ตอน idle) / **RESUME** (หลัง e-stop) |
| **SW2** | **E-STOP** -- หยุดทันที ยกเลิก navigation |

ถ้าใช้ firmware มาตรฐาน หุ่นจะพุ่งหน้าหรือหมุนทุกครั้งที่กดปุ่ม mission -- อันตราย ดังนั้น
เราปิด test-drive ที่ฝังมา หลังแก้แล้วปุ่มจะ **แค่รายงานสถานะ** ผ่าน topic `/sensor_state`
และ [`button_handler`](../../src/ttb3_mission/ttb3_mission/button_handler.py) ฝั่ง ROS
เป็นคนตัดสินใจว่าแต่ละการกดหมายถึงอะไร

แก้แค่บรรทัดเดียวในไฟล์ library ตัวเดียว ที่เหลือ (มอเตอร์, odometry, การสื่อสาร ROS) เหมือนเดิม

## firmware อยู่ใน repo นี้

ทุกอย่างอยู่ใน [`firmware/opencr/`](../../firmware/opencr/):

- `turtlebot3_burger_custom/turtlebot3_burger_custom.ino` -- sketch ที่เปิดแล้ว upload
- `disable_test_drive.patch` -- การแก้บรรทัดเดียวในไฟล์ library `turtlebot3.cpp`
- `README.md` -- คู่มือ build/flash เต็ม พร้อม path ตาม OS

## ขั้นตอน flash

คู่มือภาพ (มี screenshot) คือหน้า OpenCR setup ทางการของ ROBOTIS -- ทำตามสำหรับติดตั้ง toolchain:
**<https://emanual.robotis.com/docs/en/platform/turtlebot3/opencr_setup/>**

ฉบับย่อ:

1. **ลง Arduino IDE** (1.8.x หรือ 2.x): <https://www.arduino.cc/en/software>
2. **เพิ่ม OpenCR board package**: File → Preferences → *Additional Boards
   Manager URLs* →
   `https://raw.githubusercontent.com/ROBOTIS-GIT/OpenCR/master/arduino/opencr_release/package_opencr_index.json`
   แล้ว Tools → Board → Boards Manager → ค้น **OpenCR** → Install
3. **แก้บรรทัดเดียว**: เปิดไฟล์ `turtlebot3.cpp` ของ library (path ตาม OS อยู่ใน
   [`firmware/opencr/README.md`](../../firmware/opencr/README.md)) แล้ว comment บรรทัด
   `test_motors_with_buttons(...)` ตามที่แสดงใน `disable_test_drive.patch`
4. **เปิด sketch เรา**:
   `firmware/opencr/turtlebot3_burger_custom/turtlebot3_burger_custom.ino`
5. **เลือก** Tools → Board → **OpenCR Board** และ **Port** ที่ถูก
   (`/dev/ttyACM0` บน Linux) แล้วกด **Upload**

<!-- SCREENSHOT SLOT: Arduino IDE ที่เลือก Board=OpenCR + Port พร้อม Upload
     เซฟเป็น assets/opencr-images/arduino-board-port.png แล้ว uncomment:
![Arduino IDE เลือก board + port](../../assets/opencr-images/arduino-board-port.png) -->

## เช็คว่าใช้ได้

เปิด robot base บน Pi (`ros2 launch turtlebot3_bringup robot.launch.py`) แล้วอีก terminal:

```bash
ros2 topic echo /sensor_state
```

กด **SW1** แล้ว **SW2** -- ฟิลด์ `button` ในข้อความควรเปลี่ยน (1 = SW1, 2 = SW2) และ
**หุ่นต้องไม่ขยับ** ถ้ายังวิ่งเอง แปลว่าการแก้ library ไม่มีผล -- เช็คว่าแก้ไฟล์ที่ board
package compile จริง (ดู path ใน firmware README) ไม่ใช่สำเนาอื่น

## ต่อ servo ดิสเพนเซอร์ (GPIO ของ Pi ไม่ใช่ OpenCR)

**servo ดิสเพนเซอร์ไม่ต่อกับ OpenCR** -- ต่อเข้า **GPIO ของ Pi** ตรงๆ (อยู่ใน
[บท 6](06-run-mission.md) และ [bringup README](../../src/ttb3_bringup/README.md))
OpenCR ดูแลแค่มอเตอร์ล้อกับเซนเซอร์มาตรฐานของ TurtleBot3

## Troubleshooting

- **ไม่มี `/dev/ttyACM0`**: เช็คสาย USB และ OpenCR มีไฟไหม `ls /dev/ttyACM*` บน Pi
- **Permission denied ที่ port** (ตอน flash จากแล็ปท็อป): เพิ่มตัวเองเข้ากลุ่ม `dialout`
  (`sudo usermod -aG dialout $USER` แล้ว re-login)
- **Upload ล้มกลางคัน**: กดปุ่ม reset ของ OpenCR ตามลำดับใน e-Manual แล้วลองใหม่

---
← [6. รัน Mission จริง](06-run-mission.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [8. Foxglove →](08-foxglove.md)
