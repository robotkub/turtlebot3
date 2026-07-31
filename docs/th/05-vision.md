← [4. เข้าใจ Navigation](04-navigation.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [6. รัน Mission จริง →](06-run-mission.md)

# 5. เข้าใจ Vision

หุ่นต้องมองเห็น 2 อย่าง: **ตัวเลขบน AprilTag** (จะได้รู้ว่าต้องดีดกล่องกี่ใบ)
กับ **victim sign** (ป้ายรูปคนที่ต้องไปยืนหน้าก่อนดีดกล่อง)

## ศัพท์พื้นฐาน

| คำ | ความหมายง่ายๆ |
|---|---|
| `/image_raw` | ภาพดิบจากกล้อง (frame ต่อ frame) |
| `/image_raw/compressed` | ภาพเดียวกัน แต่บีบอัดเป็น JPEG -- ใช้ตอนส่งผ่าน WiFi ไม่กิน bandwidth มาก |
| `/camera_info` | ค่า calibration ของกล้อง (เลนส์บิดแค่ไหน ฯลฯ) |
| AprilTag | ป้ายลายบาร์โค้ดขาวดำ กล้องอ่านได้แม่นแม้มองเฉียง |

## AprilTag -- อ่านตัวเลข (R2, R3)

ไม่ได้เขียน detector เองทั้งหมด ใช้ของสำเร็จรูป `apriltag_ros` (ลงไว้แล้วผ่าน apt)
แล้วเราเขียน wrapper บางๆ คลุมอีกที:

```
กล้อง --/image_raw--> apriltag_ros (apriltag_node) --/apriltag/detections--> apriltag_detector (เราเขียน) --/tag_detections--> mission_manager
```

`apriltag_detector` (`src/ttb3_perception/ttb3_perception/apriltag_detector.py`) ทำแค่:
- เลือก tag ที่ใกล้ที่สุด (พื้นที่ใหญ่สุดในภาพ) ถ้าเห็นหลายอัน
- แปลง **tag ID เป็น box_count โดยตรง** (tag เลข 3 = ดีด 3 กล่อง) ปรับ offset/max ได้ที่ param
- ถ้าไม่เห็น tag เลยติดกัน ก็จะ publish `valid: false`

**ค่าที่ต้อง tune จริง**: `src/ttb3_perception/config/tags_36h11.yaml` -> `size:`
(ขนาดขอบดำของ tag จริง หน่วยเมตร วัดจากป้ายจริงแล้วใส่ให้ตรง มีผลกับความแม่นของ pose,
ไม่กระทบการอ่าน ID)

## Victim detector -- หาป้ายรูปคน (R4)

ทีมนี้เลือกวิธี **หาจากสี** (ไม่ได้ใช้ AprilTag ตัวที่สอง) -- ใช้ OpenCV:

1. แปลงภาพจาก BGR เป็น HSV (สีแยกจากความสว่าง ทำให้ threshold สีง่ายกว่า)
2. เลือกเฉพาะ pixel ที่อยู่ในช่วงสีที่กำหนด (`hsv_lower`/`hsv_upper`)
3. หา contour (ขอบเขตของก้อนสี) เลือกก้อนที่ใหญ่สุดที่เกิน `min_contour_area`
4. คำนวณ:
   - `bearing`: จุดกึ่งกลางก้อนสี เทียบกับกึ่งกลางภาพ (ซ้าย/ขวา) -- ใช้เลี้ยวเข้าหา
   - `apparent_size`: พื้นที่ก้อนสี / พื้นที่ภาพทั้งหมด -- ใช้ประมาณระยะ (ใหญ่ = ใกล้)

โค้ด: `src/ttb3_perception/ttb3_perception/victim_detector.py`

**ค่าที่ต้อง tune จริง**: `src/ttb3_perception/config/victim_color.yaml`

ค่า default ตั้งไว้จับป้าย victim สี**เหลือง** (คนในป้ายใส่เสื้อเหลือง) พอทดสอบใต้แสงจริง
ของสนามได้แล้ว ให้:
1. เปิด `/image_raw` ใน Foxglove ดูสีจริงของป้าย
2. sample สี pixel บนป้าย (เมาส์ชี้ดูค่า RGB หรือใช้ตัวช่วยแปลง RGB->HSV ออนไลน์)
3. แก้ `hsv_lower`/`hsv_upper` ใน config ให้ตรง แล้ว rebuild/restart node

## mission_manager ใช้ผลลัพธ์ยังไง

ตอน state `APPROACH_VICTIM` -- ใช้ `bearing`/`apparent_size` ควบคุม `/cmd_vel`
โดยตรง (ไม่ต้องส่ง goal ให้ Nav2) หมุนเข้าหา + ขับเข้าใกล้จนกว่า `apparent_size`
ถึงค่าที่กำหนด (`approach_close_size`) และอยู่กึ่งกลางภาพพอ (`approach_center_tolerance`)
แล้วค่อยหยุดสั่งดีดกล่อง -- ปรับค่าพวกนี้ได้ที่ `config/mission_params.yaml`

## ลองเล่นเอง

1. เปิด debug mode แล้วดู `/image_raw` ใน Foxglove
2. ลอง publish ปลอม `/apriltag/detections` ด้วย `ros2 topic pub` ดูว่า
   `apriltag_detector` แปลงเป็น `box_count` ถูกไหม
3. ลองแก้ `hsv_lower`/`hsv_upper` เป็นสีอื่นแล้ว restart `victim_detector` ดูผล

พร้อมแล้วไปต่อ [บท 6: รัน Mission จริง](06-run-mission.md)

---
← [4. เข้าใจ Navigation](04-navigation.md) | [กลับสารบัญ](00-index.md) | ถัดไป: [6. รัน Mission จริง →](06-run-mission.md)
