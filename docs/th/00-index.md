# RobotKub TurtleBot3 -- คู่มือเรียนรู้ (WRG Thailand 2026)

**[ English version ](../en/00-index.md)**

ยินดีต้อนรับ! ชุดเอกสารนี้เขียนขึ้นเพื่อพาไปทีละบท ตั้งแต่แกะกล่องฮาร์ดแวร์
จนถึงสั่งหุ่นวิ่งภารกิจจริงได้ครบ ไม่ต้องมีพื้นฐาน ROS2 มาก่อนก็อ่านตามได้

## เป้าหมายการเรียนรู้

อ่านจบชุดนี้แล้วควรจะ:

- [ ] ใช้ **git** เป็น (clone / pull / commit / push) พอดูแลโค้ดของทีมเองได้
- [ ] เข้าใจว่า **Navigation** (SLAM, AMCL, Nav2) ทำงานยังไง และโค้ดของเราต่อเข้าไปตรงไหน
- [ ] เข้าใจว่า **Vision** (อ่าน AprilTag, หา victim sign) ทำงานยังไง และจะไป tune ตรงไหน
- [ ] flash **firmware OpenCR** เป็น และเข้าใจว่าทำไมต้อง custom
- [ ] ใช้ **Foxglove** ดูสิ่งที่หุ่นเห็น และสั่งหุ่นจากแล็ปท็อปได้
- [ ] สั่ง **เดิน mission จบ end-to-end** ได้เอง ทั้งโหมด debug และโหมดแข่งจริง

## สารบัญ

| บท | เนื้อหา |
|---|---|
| [1. อุปกรณ์ + Flash SD Card + WiFi](01-hardware-setup.md) | ของที่ต้องมี, วิธี flash SD card ลง Raspberry Pi, ตั้งค่า WiFi/SSH ก่อนบูตครั้งแรก |
| [2. ติดตั้งซอฟต์แวร์](02-install.md) | รัน `install-humble-turtlebot3.sh`, ตั้งค่า `LDS_MODEL` ตาม lidar ที่มีจริง, build workspace |
| [3. Git พื้นฐาน](03-git-basics.md) | clone/pull/commit/push, workflow ที่ทีมใช้จริงกับ repo นี้ |
| [4. เข้าใจ Navigation](04-navigation.md) | node/topic/TF, SLAM vs AMCL, Nav2, mapping workflow, mission_manager ต่อเข้ายังไง |
| [5. เข้าใจ Vision](05-vision.md) | AprilTag detector, victim detector (สี+contour), ไฟล์ config ที่ต้อง tune |
| [6. รัน Mission จริง](06-run-mission.md) | debug vs competition launch, ปุ่ม start/e-stop/resume, ต่อ servo, checklist วันแข่ง |
| [7. OpenCR + Custom Firmware](07-opencr.md) | OpenCR ทำอะไร, ทำไมต้อง flash custom firmware (ปุ่ม), ขั้นตอน flash ด้วย Arduino IDE |
| [8. Foxglove](08-foxglove.md) | connect visualizer, import dashboard, เรียก service, ดู mission state |

## เอกสารอ้างอิงอื่นๆ ในโปรเจกต์นี้

- [`../../README.md`](../../README.md) -- README หลักของ repo (สรุปสั้น, ไว้เปิดดูเร็วๆ)
- [`../../src/ttb3_bringup/README.md`](../../src/ttb3_bringup/README.md) -- รายละเอียด launch argument ทั้งหมด + checklist ฮาร์ดแวร์
- [`../../maps/README.md`](../../maps/README.md) -- เรื่อง map ที่ save ไว้
- SRS ฉบับเต็ม: `SRS_TurtleBot3_WRG2026.docx`
- คู่มือ TurtleBot3 ทางการ: <https://emanual.robotis.com/docs/en/platform/turtlebot3/overview/>

ไม่แน่ใจว่าจะเริ่มตรงไหน? เริ่มที่ [บท 1](01-hardware-setup.md) เลยครับ
