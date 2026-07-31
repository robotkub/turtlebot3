"""Pure vision helpers with NO ROS imports.

Everything here works on plain numpy images / plain data, so it can be unit
tested in CI without installing ROS (see test/test_vision.py and the
vision-tests GitHub Actions workflow). The ROS nodes
(victim_detector.py / apriltag_detector.py) are thin wrappers that convert
ROS messages to/from these functions.
"""
import cv2
import numpy as np


# ---- victim sign (yellow blob) detection --------------------------------

def victim_mask(bgr, hsv_lower, hsv_upper, hsv_lower2, hsv_upper2):
    """Binary mask of pixels within either HSV range. Two ranges support hues
    that wrap around 0/180 (e.g. red); for yellow both ranges are the same."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array(hsv_lower, np.uint8), np.array(hsv_upper, np.uint8))
    m2 = cv2.inRange(hsv, np.array(hsv_lower2, np.uint8), np.array(hsv_upper2, np.uint8))
    mask = cv2.bitwise_or(m1, m2)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    return mask


def detect_victim(bgr, hsv_lower, hsv_upper, hsv_lower2, hsv_upper2,
                  min_contour_area, annotate=False):
    """Find the largest color blob (the victim sign) in a BGR image.

    Returns a dict: detected, and when detected also bearing (-1..+1 left/right
    of center), apparent_size (bbox area / image area), image_x, image_y.
    If annotate is True, also returns 'bbox' (x, y, w, h) for drawing.
    """
    height, width = bgr.shape[:2]
    mask = victim_mask(bgr, hsv_lower, hsv_upper, hsv_lower2, hsv_upper2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = max(contours, key=cv2.contourArea) if contours else None

    if best is None or cv2.contourArea(best) < min_contour_area:
        return {'detected': False}

    x, y, w, h = cv2.boundingRect(best)
    cx, cy = x + w / 2.0, y + h / 2.0
    result = {
        'detected': True,
        'bearing': float((cx - width / 2.0) / (width / 2.0)),
        'apparent_size': float((w * h) / (width * height)),
        'image_x': float(cx),
        'image_y': float(cy),
    }
    if annotate:
        result['bbox'] = (int(x), int(y), int(w), int(h))
    return result


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
