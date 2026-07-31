← [1. อุปกรณ์ + SD Card](01-hardware-setup.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [3. Git พื้นฐาน →](03-git-basics.md)

# 2. ติดตั้งซอฟต์แวร์

ทำซ้ำสองรอบ: **รอบนึงบน Pi (หุ่น), อีกรอบบนแล็ปท็อป** สคริปต์ตัวเดียวกันจะรู้เองว่ากำลังรันอยู่บนเครื่องไหน

## 2.1 รัน install script

```bash
git clone https://github.com/robotkub/turtlebot3.git ~/turtlebot3_ws
cd ~/turtlebot3_ws/scripts
chmod +x install-humble-turtlebot3.sh
./install-humble-turtlebot3.sh
```

(ยังไม่รู้จัก `git clone` ดีพอ? อ่าน [บท 3: Git พื้นฐาน](03-git-basics.md) ก่อนก็ได้ แล้วค่อยย้อนกลับมาทำขั้นนี้)

สคริปต์เช็คเองว่ากำลังรันบน Raspberry Pi หรือแล็ปท็อป:

- **บน Pi**: ลงแบบ headless (`ros-base`) -- ไม่มี RViz2/rqt เพราะ Pi ไม่มีจอต่ออยู่แล้วก็ใช้ไม่ได้
- **บนแล็ปท็อป**: ลงแบบ desktop เต็ม (`ros-humble-desktop`) -- ได้ RViz2 + rqt มาด้วยสำหรับดู map/debug

ถ้า auto-detect เดาผิด บังคับเองได้:
```bash
./install-humble-turtlebot3.sh pi
./install-humble-turtlebot3.sh laptop
```

สคริปต์นี้ลงให้ครบ: ROS2 Humble, TurtleBot3 packages, Nav2, SLAM Toolbox,
Cartographer, AprilTag, Foxglove Bridge, CycloneDDS -- แล้ว build workspace
ให้เลยรอบแรก บน **Pi** ยังลง servo library (`python3-gpiozero`, `python3-lgpio`)
สำหรับดิสเพนเซอร์ และตั้ง `LDS_MODEL` + alias ที่ใช้บ่อย (`reset_pose`, `estop`,
`foxglove_start`, `rebuild`) ใน `~/.bashrc` ให้ด้วย

**หลังรันเสร็จ**: ปิด terminal แล้วเปิดใหม่ (หรือ `source ~/.bashrc`) แล้วเช็ค:

```bash
echo $ROS_DISTRO         # -> humble
echo $TURTLEBOT3_MODEL    # -> burger
```

## 2.2 ตั้งค่า `LDS_MODEL` ตาม lidar ที่มีจริง

**สำคัญมาก** -- ถ้าข้ามขั้นนี้ พอต่อหุ่นจริง `robot.launch.py` จะ **crash ทันที**
(`KeyError: 'LDS_MODEL'`) เพราะมันอ่านตัวแปรนี้เพื่อเลือกว่าจะ launch driver
lidar ตัวไหน

เช็คก่อนว่า lidar ที่มีจริงเป็นรุ่นอะไร (ดูสติกเกอร์ใต้ตัว lidar หรือใบสเปคตอนซื้อ):

| รุ่น | ค่าที่ต้องตั้ง | driver ที่ใช้ |
|---|---|---|
| LDS-01 (ของโปรเจกต์นี้) | `LDS_MODEL=LDS-01` | `hls_lfcd_lds_driver` (มากับ apt แล้ว) |
| LDS-02 / LD08 | `LDS_MODEL=LDS-02` | `ld08_driver` (ต้อง clone+build เองจาก source, apt ไม่มี) |

install script ตั้ง `LDS_MODEL=LDS-01` ให้ใน `~/.bashrc` แล้ว ถ้าของทีมเป็นรุ่นอื่น
ให้แก้ (และถ้าเป็น LDS-02/LD08 ต้อง build `ld08_driver` จาก source เพิ่มด้วย):
```bash
grep LDS_MODEL ~/.bashrc          # เช็คว่ามีแล้ว
# ถ้าจะแก้ ให้แก้ใน ~/.bashrc แล้ว:
source ~/.bashrc
```

> ถ้าใช้ LDS-01 (ตามที่ทีมนี้ใช้อยู่) ไม่ต้องทำอะไรเพิ่มแล้ว เพราะ
> `ros-humble-turtlebot3-bringup` ดึง `hls_lfcd_lds_driver` มาให้อัตโนมัติผ่าน
> apt dependency อยู่แล้ว และ install script ตั้งตัวแปรให้แล้ว

## 2.3 ROS_DOMAIN_ID -- อย่าลืมก่อนวันแข่ง

`install-humble-turtlebot3.sh` ตั้ง `ROS_DOMAIN_ID=42` (ค่า default) ไว้ให้ก่อน
เพื่อให้ทีมทดสอบกันได้เลย **แต่ก่อนวันแข่งจริง ทุกคนในทีมต้องเปลี่ยนเป็นเลขที่ไม่ซ้ำใคร**
(แก้ใน `~/.bashrc` ทั้งบน Pi และแล็ปท็อป, ต้องตรงกันทั้งสองเครื่อง) เพราะสนามแข่งมี
6-7 ทีมใช้ WiFi router ตัวเดียวกัน ถ้าใช้เลข default เหมือนกันจะเห็นหุ่นทีมอื่นปนกับของตัวเอง

## 2.4 Build workspace ของเรา

ถ้ายังไม่ได้ build (หรือแก้โค้ดแล้วอยากลอง build ใหม่):

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install
source install/setup.bash
```

เช็คว่า package ของเราขึ้นครบ:
```bash
ros2 pkg list | grep ttb3
# ต้องเห็น: ttb3_bringup ttb3_dispenser ttb3_mission ttb3_msgs ttb3_perception
```

ครบแล้วไปต่อ [บท 3: Git พื้นฐาน](03-git-basics.md) ได้เลย

---
← [1. อุปกรณ์ + SD Card](01-hardware-setup.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [3. Git พื้นฐาน →](03-git-basics.md)
