"""Vision unit tests -- run in CI with NO ROS (just OpenCV + numpy +
pupil-apriltags). They exercise the two things the vision stack must get right:

  1. AprilTag: read a tag from an image and produce the right box count.
  2. Victim: detect the yellow victim sign, and NOT false-trigger on non-yellow
     people -- while the image is randomly rotated, tilted left/right, and its
     exposure changed, to prove the detector is robust.

The heavy lifting is in ttb3_perception.vision_core (ROS-free on purpose).
"""
import os
import sys

import cv2
import numpy as np
import pytest

# Make the ROS-free package module importable without installing the ROS pkg.
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from ttb3_perception.vision_core import (  # noqa: E402
    corner_area,
    detect_victim,
    tag_id_to_box_count,
)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# Yellow victim HSV band (matches config/victim_color.yaml).
VICTIM_PARAMS = dict(
    hsv_lower=[20, 100, 100], hsv_upper=[35, 255, 255],
    hsv_lower2=[20, 100, 100], hsv_upper2=[35, 255, 255],
    min_contour_area=500,
)


# ---- augmentation --------------------------------------------------------

def _augment(bgr, rng, max_angle=25.0, max_tilt=0.15, gain_range=(0.5, 1.7)):
    """Randomly rotate, shear left/right (tilt), and change exposure. White
    background so rotation doesn't invent colored corners."""
    h, w = bgr.shape[:2]
    angle = rng.uniform(-max_angle, max_angle)
    tilt = rng.uniform(-max_tilt, max_tilt)
    gain = rng.uniform(*gain_range)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 2] = np.clip(hsv[..., 2] * gain, 0, 255)  # exposure
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    m[0, 1] += tilt  # horizontal shear = tilt left/right
    return cv2.warpAffine(out, m, (w, h), borderValue=(255, 255, 255))


def _load(*parts):
    path = os.path.join(DATA, *parts)
    img = cv2.imread(path)
    assert img is not None, f'could not read test image: {path}'
    return img


# ---- victim detection ----------------------------------------------------

YELLOW_POSITIVES = ['pos_yellow_ref.png', 'pos_yellow_couple.png',
                    'pos_yellow_crying_kids.png']
NON_YELLOW_NEGATIVES = ['neg_blue_boy.png', 'neg_couple_greenblue.png']


@pytest.mark.parametrize('name', YELLOW_POSITIVES)
def test_victim_detected_upright(name):
    assert detect_victim(_load('victim', name), **VICTIM_PARAMS)['detected']


@pytest.mark.parametrize('name', NON_YELLOW_NEGATIVES)
def test_non_yellow_not_detected_upright(name):
    assert not detect_victim(_load('victim', name), **VICTIM_PARAMS)['detected']


@pytest.mark.parametrize('name', YELLOW_POSITIVES)
def test_victim_robust_to_rotation_tilt_exposure(name):
    """Yellow sign stays detected across random rotate/tilt/exposure."""
    img = _load('victim', name)
    rng = np.random.default_rng(1234)
    trials = 30
    hits = sum(detect_victim(_augment(img, rng), **VICTIM_PARAMS)['detected']
               for _ in range(trials))
    assert hits >= int(0.9 * trials), f'{name}: only {hits}/{trials} detections'


@pytest.mark.parametrize('name', NON_YELLOW_NEGATIVES)
def test_negatives_stay_negative_under_augmentation(name):
    """Non-yellow people never false-trigger, even augmented."""
    img = _load('victim', name)
    rng = np.random.default_rng(1234)
    trials = 30
    false_hits = sum(detect_victim(_augment(img, rng), **VICTIM_PARAMS)['detected']
                     for _ in range(trials))
    assert false_hits == 0, f'{name}: {false_hits}/{trials} false detections'


def test_victim_bearing_sign():
    """A yellow blob on the left gives negative bearing; on the right, positive."""
    left = np.full((200, 400, 3), 255, np.uint8)
    left[80:160, 20:120] = (0, 255, 255)  # BGR yellow, left side
    right = np.full((200, 400, 3), 255, np.uint8)
    right[80:160, 280:380] = (0, 255, 255)  # right side
    rl = detect_victim(left, **VICTIM_PARAMS)
    rr = detect_victim(right, **VICTIM_PARAMS)
    assert rl['detected'] and rr['detected']
    assert rl['bearing'] < 0 < rr['bearing']


# ---- AprilTag reading ----------------------------------------------------

def _apriltag_detector():
    pupil = pytest.importorskip('pupil_apriltags')
    return pupil.Detector(families='tag36h11')


@pytest.mark.parametrize('tag_id', [1, 2, 3, 5])
def test_apriltag_read_id_upright(tag_id):
    det = _apriltag_detector()
    gray = cv2.imread(os.path.join(DATA, 'apriltag', f'tag36h11_{tag_id}.png'),
                      cv2.IMREAD_GRAYSCALE)
    assert gray is not None
    results = det.detect(gray)
    ids = [r.tag_id for r in results]
    assert tag_id in ids, f'expected to read tag {tag_id}, got {ids}'
    # the number read maps straight to the box count
    assert tag_id_to_box_count(tag_id) == min(tag_id, 5)


@pytest.mark.parametrize('tag_id', [2, 3])
def test_apriltag_read_robust_to_rotation_exposure(tag_id):
    """Reading the tag still works when the image is rotated + exposure-shifted
    (milder than victim -- extreme rotation clips a tag's quiet zone)."""
    det = _apriltag_detector()
    bgr = cv2.imread(os.path.join(DATA, 'apriltag', f'tag36h11_{tag_id}.png'))
    rng = np.random.default_rng(7)
    trials, hits = 20, 0
    for _ in range(trials):
        aug = _augment(bgr, rng, max_angle=15.0, max_tilt=0.05, gain_range=(0.6, 1.4))
        gray = cv2.cvtColor(aug, cv2.COLOR_BGR2GRAY)
        if tag_id in [r.tag_id for r in det.detect(gray)]:
            hits += 1
    assert hits >= int(0.8 * trials), f'tag {tag_id}: only {hits}/{trials} reads'


# ---- pure helpers --------------------------------------------------------

def test_tag_id_to_box_count_clamps():
    assert tag_id_to_box_count(3) == 3
    assert tag_id_to_box_count(9, max_count=5) == 5   # clamp high
    assert tag_id_to_box_count(-2) == 0               # clamp low
    assert tag_id_to_box_count(2, offset=1) == 3      # offset applied


def test_corner_area_unit_square():
    assert corner_area([(0, 0), (10, 0), (10, 10), (0, 10)]) == pytest.approx(100.0)
