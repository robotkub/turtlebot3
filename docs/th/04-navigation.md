← [3. Git พื้นฐาน](03-git-basics.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [5. เข้าใจ Vision →](05-vision.md)

# 4. เข้าใจ Navigation

## ศัพท์พื้นฐานก่อน

| คำ | ความหมายง่ายๆ |
|---|---|
| **Node** | โปรแกรมเล็กๆ หนึ่งตัว ทำงานหนึ่งอย่าง คุยกับตัวอื่นผ่าน topic |
| **Topic** | ช่องทางสื่อสารที่มีชื่อ (เช่น `/cmd_vel`) node ไหนจะ publish (พูด) หรือ subscribe (ฟัง) ก็ได้ |
| **TF** | ระบบบอกว่า "จุดนี้อยู่ตรงไหนเทียบกับจุดนั้น" เช่น กล้องอยู่ตรงไหนเทียบกับตัวหุ่น |
| **`/odom`** | ตำแหน่งหุ่นที่คำนวณจากล้อหมุนไปกี่รอบ (เพี้ยนสะสมได้ถ้าล้อลื่น) |
| **`/map`** | แผนที่ของสนามที่ build ไว้แล้ว |
| **SLAM** | สร้างแผนที่ + หาตำแหน่งตัวเองไปพร้อมกัน (ใช้ตอนยังไม่มีแผนที่) |
| **AMCL** | หาตำแหน่งตัวเองบนแผนที่ที่ **มีอยู่แล้ว** (เร็ว/แม่นกว่า SLAM ถ้าแผนที่ไม่เปลี่ยน) |
| **Nav2** | ระบบวางแผนเส้นทาง + ขับไปเอง หลบกำแพง เมื่อบอกพิกัดปลายทาง |

## Layer การทำงาน (จากล่างขึ้นบน)

1. **OpenCR firmware** -- publish `/odom`, `/imu`, `/scan` (lidar), `/sensor_state`; subscribe `/cmd_vel`
2. **ROS2** -- ระบบส่งข้อความกลางที่ทำให้ node ทุกตัวคุยกันได้
3. **Nav2 + SLAM/AMCL** -- ของสำเร็จรูป (ไม่ได้เขียนเอง) ที่เรา config ให้ทำงานกับหุ่นเรา
4. **โค้ดของเรา** -- `mission_manager` เป็นคนสั่ง Nav2 ว่า "ไปตรงนี้ที" ผ่าน action `NavigateToPose`

## ขั้นตอนสร้างแผนที่ (ทำครั้งเดียวต่อสนามหนึ่งแบบ)

ใช้ 3 สคริปต์ใน `scripts/` เรียงตามลำดับ:

| ขั้น | สคริปต์ | รันที่ | ทำอะไร |
|---|---|---|---|
| 1 | `1_map_robot.sh` | **Pi** | เปิดล้อ/lidar/IMU -- ปล่อยรันไว้เฉยๆ |
| 2 | `2_map_start.sh` | **แล็ปท็อป** | เช็คว่าเห็นหุ่นไหม แล้วเปิด SLAM (Cartographer) + RViz2 |
| 3 | `3_map_save.sh <name>` | **แล็ปท็อป** | เซฟแผนที่ที่ได้ลง `maps/<name>.yaml` + `.pgm` |

```bash
# terminal 1 (Pi)
./scripts/1_map_robot.sh

# terminal 2 (laptop) -- รอ terminal 1 ขึ้นก่อน
./scripts/2_map_start.sh

# terminal 3 (laptop) -- ขับหุ่นเดินสำรวจสนามให้ทั่ว
ros2 run turtlebot3_teleop teleop_keyboard

# พอแผนที่ใน RViz ไม่มีส่วนดำ (unknown) เหลือในกำแพงแล้ว
./scripts/3_map_save.sh arena_v1
```

รายละเอียดเพิ่มเติม (เช่น troubleshoot ตอน `/scan` หาไม่เจอ): [`../../maps/README.md`](../../maps/README.md)

## ตอนรัน mission จริง -- navigation ทำงานยังไง

`ttb3_bringup`'s `debug.launch.py`/`competition.launch.py` จะรวม Nav2 bringup
(`nav2_bringup/bringup_launch.py`) เข้ากับแผนที่ที่เซฟไว้ (`maps/arena_v1.yaml`
เป็นค่า default, เปลี่ยนได้ด้วย `map:=...`) โหมดนี้ใช้ **AMCL** (ไม่ใช่ SLAM) เพราะ
มีแผนที่อยู่แล้ว ไม่ต้องสร้างใหม่ทุกรอบ

## โค้ดของเราต่อเข้า Nav2 ตรงไหน

ไฟล์หลัก: `src/ttb3_mission/ttb3_mission/mission_manager.py`

- **SEARCH**: ส่งพิกัด waypoint ทีละจุด (จาก `config/mission_params.yaml`) ให้ Nav2
  ผ่าน action `NavigateToPose` วนไปเรื่อยๆ จนกว่าจะเจอทั้ง tag และ victim sign
- **RETURN_HOME**: ส่ง goal กลับไปที่พิกัด START (ค่า default ตรงกับ alias
  `reset_pose` ใน `.bashrc`)
- **Stuck watchdog**: เช็ค `/odom` ว่าตำแหน่งขยับจริงไหมในช่วง 10 วินาทีล่าสุด
  ถ้าไม่ขยับเลย (ติดกำแพง/ล้อหมุนฟรี) จะยกเลิก goal แล้วหยุดแทนที่จะดันต่อไปเรื่อยๆ
- **ResetToStart service**: ตอนกด SW1 จะ republish `/initialpose` กลับไปที่
  START pose (แก้แค่ AMCL เชื่อว่าอยู่ตรงไหน ไม่ได้ลบคะแนน/ความคืบหน้าที่ทำไปแล้ว)

## ลองเล่นเอง

1. เปิด debug mode (`ros2 launch ttb3_bringup debug.launch.py`) แล้วดู `/mission_status` ใน Foxglove ว่า state เปลี่ยนยังไง
2. ลองส่ง goal มือ: `ros2 topic pub -1 /initialpose ...` (ปรับตำแหน่งเริ่มต้น)
3. ลองกด SW1/SW2 จริง (หรือ publish `/sensor_state` ปลอมด้วย `ros2 topic pub`) ดูว่า state เปลี่ยนตามที่คาดไหม

พร้อมแล้วไปต่อ [บท 5: เข้าใจ Vision](05-vision.md)

---
← [3. Git พื้นฐาน](03-git-basics.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [5. เข้าใจ Vision →](05-vision.md)
