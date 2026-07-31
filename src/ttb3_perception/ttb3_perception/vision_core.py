"""Pure vision helpers with NO ROS imports.

Everything here works on plain numpy images / plain data, so it can be unit
tested in CI without installing ROS (see test/test_vision.py and the
vision-tests GitHub Actions workflow). The ROS nodes
(victim_detector.py / apriltag_detector.py) are thin wrappers that convert
ROS messages to/from these functions.
"""
import cv2
import numpy as np

# MobileNet-SSD (PASCAL VOC) class index for "person".
PERSON_CLASS = 15


# ---- victim sign (a human figure) detection ------------------------------

def load_person_net(prototxt_path, caffemodel_path):
    """Load the MobileNet-SSD person detector. Needs OpenCV < 5
    (readNetFromCaffe); the Pi ships 4.5.4."""
    return cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)


def detect_person(bgr, net, conf_threshold=0.45):
    """Detect the victim sign as a HUMAN FIGURE (not by color) using the DNN.

    Returns a dict: detected, and when detected also confidence, bearing
    (-1..+1 left/right of center), apparent_size (bbox area / image area),
    image_x, image_y, and bbox (x, y, w, h). Picks the highest-confidence
    person box above conf_threshold.
    """
    height, width = bgr.shape[:2]
    net.setInput(cv2.dnn.blobFromImage(bgr, 0.007843, (300, 300), 127.5))
    detections = net.forward()

    best = None
    for i in range(detections.shape[2]):
        if int(detections[0, 0, i, 1]) != PERSON_CLASS:
            continue
        conf = float(detections[0, 0, i, 2])
        if conf < conf_threshold:
            continue
        if best is None or conf > best[0]:
            box = detections[0, 0, i, 3:7] * np.array([width, height, width, height])
            best = (conf, box)

    if best is None:
        return {'detected': False}

    conf, (x0, y0, x1, y1) = best
    x0, y0 = max(0.0, x0), max(0.0, y0)
    x1, y1 = min(float(width), x1), min(float(height), y1)
    bw, bh = max(0.0, x1 - x0), max(0.0, y1 - y0)
    cx, cy = x0 + bw / 2.0, y0 + bh / 2.0
    return {
        'detected': True,
        'confidence': conf,
        'bearing': float((cx - width / 2.0) / (width / 2.0)),
        'apparent_size': float((bw * bh) / (width * height)),
        'image_x': float(cx),
        'image_y': float(cy),
        'bbox': (int(x0), int(y0), int(bw), int(bh)),
    }


# ---- AprilTag helpers ----------------------------------------------------

def corner_area(corners):
    """Shoelace area (pixel^2) of a tag's 4 corners. `corners` is a sequence of
    (x, y) pairs. Used to pick the closest/largest tag when several are seen."""
    area = 0.0
    n = len(corners)
    for i in range(n):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def tag_id_to_box_count(tag_id, offset=0, max_count=5):
    """Map a decoded AprilTag ID to the number of boxes to dispense, clamped to
    [0, max_count]. offset lets the arena map tag IDs onto counts if needed."""
    return max(0, min(max_count, tag_id + offset))
