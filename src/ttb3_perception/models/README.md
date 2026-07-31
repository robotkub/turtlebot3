# Vision model

`MobileNetSSD_deploy.{prototxt,caffemodel}` — MobileNet-SSD trained on PASCAL
VOC (20 classes incl. `person` = class 15). Used by `victim_detector` to detect
the human victim sign, and by the vision tests. Loaded with
`cv2.dnn.readNetFromCaffe` (needs OpenCV < 5; the Pi ships 4.5.4).

Source mirror: https://github.com/djmv/MobilNet_SSD_opencv (MIT).
