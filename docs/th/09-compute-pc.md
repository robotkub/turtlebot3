← [8. Foxglove](08-foxglove.md) | [กลับหน้าสารบัญ](00-index.md)

# 9. ย้ายภาระประมวลผล Mapping & Nav2 Debug มาที่แล็ปท็อป (Docker)

Raspberry Pi 3 B+ (quad-core ARM Cortex-A53 @ 1.4 GHz, 1 GB RAM) บนหุ่นยนต์มีทรัพยากรจำกัด แม้จะคุมมอเตอร์ อ่านเซนเซอร์ รัน perception และภารกิจหลักได้ดี แต่การรัน SLAM (Cartographer) และ Nav2 localization/planning หนักๆ ไปพร้อมกันขณะสร้างแผนที่หรือทดสอบจูนระบบอาจสร้างภาระให้เครื่องมากเกินไป

เพื่อแก้ปัญหานี้ในขั้นตอนพัฒนาและทดสอบ จึงย้ายการประมวลผลของ Cartographer และ Nav2 debug แยกมารันใน Docker container บนแล็ปท็อปแทนการลง ROS 2 แบบ bare-metal บนเครื่อง

> [!IMPORTANT]
> **สำหรับโหมด Debug/Testing เท่านั้น!**
> การย้ายการประมวลผลนี้ใช้สำหรับ **การสร้างแผนที่ (mapping) การจูน และการทดสอบ debug เท่านั้น** ในวันแข่งจริง `competition.launch.py` จะรันบน Raspberry Pi แบบ standalone เต็มรูปแบบ โดยไม่ต้องพึ่งพาแล็ปท็อป (ตรงตามข้อกำหนด SRS R10 / N3/N4 เรื่องแบนด์วิดธ์ WiFi ในสนามแข่ง)

---

## สถาปัตยกรรมระบบ (Architecture)

- **อุปกรณ์กายภาพ**: มี 2 เครื่องเหมือนเดิม คือ Raspberry Pi (บนหุ่น) + แล็ปท็อป
- **สภาพแวดล้อมบนแล็ปท็อป**: รัน ROS 2 Humble ผ่าน Docker container (`ttb3-compute`) โดยไม่ต้องติดตั้ง ROS 2 แบบ bare-metal บนระบบปฏิบัติการของแล็ปท็อป
- **การเชื่อมต่อเครือข่าย**: ใช้ `network_mode: host` เพื่อเปิดให้ ROS 2 DDS discovery ทำงานผ่าน UDP multicast ระหว่างสองเครื่องได้อย่างสมบูรณ์
- **การแสดงผล (Visualization)**: ใช้ Foxglove Bridge (`visualize:=true`) ที่ถูกรวมอยู่ใน launch file (เชื่อมต่อ WebSocket ที่ `ws://localhost:8765`) ทำให้ไม่ต้องใช้ RViz ภายใน container

---

## การเตรียมระบบครั้งแรก (One-Time Setup)

สั่ง build Docker image สำหรับประมวลผลบนแล็ปท็อป (รันจากโฟลเดอร์หลักของโปรเจกต์):

```bash
docker compose build
```

ระบบจะทำการคอมไพล์ `ttb3_bringup` ภายในภาพ ROS 2 Humble headless ที่ติดตั้ง Cartographer, Nav2, Foxglove Bridge และ CycloneDDS ไว้อย่างครบถ้วน

---

## ขั้นตอนการทำงานที่ 1: การสร้างแผนที่ (Cartographer + Map Autosaver)

1. **บน Raspberry Pi**: สั่งเปิดระบบฐานหุ่นยนต์ (OpenCR bridge & Lidar):
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **บนแล็ปท็อป**: สั่งรัน Cartographer mapping ผ่าน Docker:
   ```bash
   ROS_DOMAIN_ID=42 docker compose run --rm ttb3-compute \
     ros2 launch ttb3_bringup mapping.launch.py map_path:=arena_v1 visualize:=true
   ```

3. **ดูผลลัพธ์และบังคับหุ่น**:
   - เปิด Foxglove Studio (`ws://localhost:8765`) เพื่อดูแผนที่กำลังสร้างแบบ real-time
   - บังคับหุ่นเดินสำรวจพื้นที่จากแล็ปท็อปหรือ Pi:
     ```bash
     ros2 run turtlebot3_teleop teleop_keyboard
     ```
   - เมื่อสร้างแผนที่เสร็จแล้ว ให้กด `Ctrl-C` ที่เทอร์มินัลของแล็ปท็อป ไฟล์แผนที่ (`arena_v1.pgm` และ `arena_v1.yaml`) จะถูกบันทึกลงในโฟลเดอร์ `./maps/` บนเครื่องแล็ปท็อปโดยอัตโนมัติผ่าน volume mount (`./maps:/maps`)

---

## ขั้นตอนการทำงานที่ 2: การทดสอบ Nav2 Standalone & Tuning

สำหรับการทดสอบและจูน Nav2 (AMCL + Path Planner) กับแผนที่ที่บันทึกไว้:

1. **บน Raspberry Pi**: สั่งเปิดระบบฐานหุ่นยนต์:
   ```bash
   ros2 launch turtlebot3_bringup robot.launch.py
   ```

2. **บนแล็ปท็อป**: สั่งรัน Nav2 standalone ใน Docker:
   ```bash
   ROS_DOMAIN_ID=42 docker compose run --rm ttb3-compute \
     ros2 launch ttb3_bringup navigation.launch.py map:=/maps/arena_v1.yaml visualize:=true
   ```

3. **แสดงผลและกำหนดจุดเป้าหมาย**:
   - เชื่อมต่อ Foxglove ไปที่ `ws://localhost:8765`
   - กำหนด 2D Pose Estimate และ Nav Goal ผ่าน Foxglove

---

## ข้อกำหนดสำคัญและการตั้งค่า

- **`ROS_DOMAIN_ID`**: ต้องตรงกันระหว่าง Raspberry Pi และแล็ปท็อป (ค่าเริ่มต้นคือ `42`) ตั้งค่าผ่าน environment variable ก่อนสั่ง `docker compose run`
- **DDS Middleware**: ใช้ `rmw_cyclonedds_cpp` ตรงกันทั้งสองฝ่ายเพื่อความเสถียรในการ discovery
- **Host Volume Mounting**: โฟลเดอร์ `./maps` บนแล็ปท็อปถูกผูกกับ `/maps` ใน container ทำให้แผนที่ที่เซฟได้อยู่บนดิสก์ของเครื่องแล็ปท็อปทันที

---

← [8. Foxglove](08-foxglove.md) | [กลับหน้าสารบัญ](00-index.md)
