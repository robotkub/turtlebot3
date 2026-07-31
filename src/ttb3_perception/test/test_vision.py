"""Vision unit tests -- run in CI with NO ROS (just OpenCV + numpy +
pupil-apriltags). They exercise the two things the vision stack must get right:

  1. AprilTag: read a tag from an image and produce the right box count,
     including when the tag is seen at an angle (perspective).
  2. Victim: detect the yellow victim sign, and NOT false-trigger on non-yellow
     people -- while the image is flipped, rotated in 90 degree steps, viewed
     from a high/low/side angle (perspective), and randomly rotated/tilted/
     re-exposed.

Test images = the real reference photos (victim/*.png) + generated synthetic
figures (victim/synthetic/*.png, see generate_synthetic.py). Any file named
pos_*.png must be detected as a victim; neg_*.png must not.

The heavy lifting is in ttb3_perception.vision_core (ROS-free on purpose).
"""
import glob
import os
import sys

import cv2
import numpy as np
import pytest

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


# ---- image discovery -----------------------------------------------------

def _victim_images(prefix):
    """All victim test images (real + synthetic) whose filename starts with
    prefix ('pos_' or 'neg_'), as (id, path) pairs for nice pytest ids."""
    paths = sorted(glob.glob(os.path.join(DATA, 'victim', f'{prefix}*.png')) +
                   glob.glob(os.path.join(DATA, 'victim', 'synthetic', f'{prefix}*.png')))
    return [(os.path.relpath(p, DATA), p) for p in paths]


POSITIVES = _victim_images('pos_')
NEGATIVES = _victim_images('neg_')


def _load(path):
    img = cv2.imread(path)
    assert img is not None, f'could not read test image: {path}'
    return img


# ---- augmentations -------------------------------------------------------

def _orient(img, k):
    """k: 0..3 -> rotate 0/90/180/270 deg; 4 -> horizontal flip (front/back
    mirror); 5 -> vertical flip."""
    if k < 4:
        return np.ascontiguousarray(np.rot90(img, k))
    return cv2.flip(img, 1 if k == 4 else 0)


ORIENTATIONS = {'rot0': 0, 'rot90': 1, 'rot180': 2, 'rot270': 3,
                'hflip': 4, 'vflip': 5}


def _perspective(img, kind, amount=0.25):
    """Warp the image plane to fake a camera angle:
    pitch_down = looking down on the sign, pitch_up = looking up at it,
    yaw_left / yaw_right = seen from the side."""
    h, w = img.shape[:2]
    s = amount
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    if kind == 'pitch_down':
        dst = np.float32([[w * s, 0], [w * (1 - s), 0], [w, h], [0, h]])
    elif kind == 'pitch_up':
        dst = np.float32([[0, 0], [w, 0], [w * (1 - s), h], [w * s, h]])
    elif kind == 'yaw_left':
        dst = np.float32([[0, 0], [w, h * s], [w, h * (1 - s)], [0, h]])
    elif kind == 'yaw_right':
        dst = np.float32([[0, h * s], [w, 0], [w, h], [0, h * (1 - s)]])
    else:
        raise ValueError(kind)
    m = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, m, (w, h), borderValue=(255, 255, 255))


CAMERA_ANGLES = ['pitch_down', 'pitch_up', 'yaw_left', 'yaw_right']


def _random_augment(bgr, rng, max_angle=25.0, max_tilt=0.15, gain_range=(0.5, 1.7)):
    """Random rotation, left/right tilt (shear), and exposure change."""
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 2] = np.clip(hsv[..., 2] * rng.uniform(*gain_range), 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-max_angle, max_angle), 1.0)
    m[0, 1] += rng.uniform(-max_tilt, max_tilt)
    return cv2.warpAffine(out, m, (w, h), borderValue=(255, 255, 255))


def _detected(img):
    return detect_victim(img, **VICTIM_PARAMS)['detected']


# ---- victim: orientation (90 deg steps + flips) --------------------------

@pytest.mark.parametrize('name,path', POSITIVES)
@pytest.mark.parametrize('orient', list(ORIENTATIONS))
def test_positive_detected_every_orientation(name, path, orient):
    assert _detected(_orient(_load(path), ORIENTATIONS[orient])), \
        f'{name} not detected at {orient}'


@pytest.mark.parametrize('name,path', NEGATIVES)
@pytest.mark.parametrize('orient', list(ORIENTATIONS))
def test_negative_rejected_every_orientation(name, path, orient):
    assert not _detected(_orient(_load(path), ORIENTATIONS[orient])), \
        f'{name} FALSE-detected at {orient}'


# ---- victim: camera angle (perspective) ----------------------------------

@pytest.mark.parametrize('name,path', POSITIVES)
@pytest.mark.parametrize('angle', CAMERA_ANGLES)
def test_positive_detected_from_camera_angle(name, path, angle):
    assert _detected(_perspective(_load(path), angle)), \
        f'{name} not detected from {angle}'


@pytest.mark.parametrize('name,path', NEGATIVES)
@pytest.mark.parametrize('angle', CAMERA_ANGLES)
def test_negative_rejected_from_camera_angle(name, path, angle):
    assert not _detected(_perspective(_load(path), angle)), \
        f'{name} FALSE-detected from {angle}'


# ---- victim: random rotation/tilt/exposure -------------------------------

@pytest.mark.parametrize('name,path', POSITIVES)
def test_positive_robust_random_augment(name, path):
    img = _load(path)
    rng = np.random.default_rng(1234)
    trials = 20
    hits = sum(_detected(_random_augment(img, rng)) for _ in range(trials))
    assert hits >= int(0.9 * trials), f'{name}: only {hits}/{trials} detections'


@pytest.mark.parametrize('name,path', NEGATIVES)
def test_negative_no_false_positive_random_augment(name, path):
    img = _load(path)
    rng = np.random.default_rng(1234)
    trials = 20
    bad = sum(_detected(_random_augment(img, rng)) for _ in range(trials))
    assert bad == 0, f'{name}: {bad}/{trials} false detections'


def test_victim_bearing_sign():
    """A yellow blob on the left gives negative bearing; on the right, positive."""
    left = np.full((200, 400, 3), 255, np.uint8)
    left[80:160, 20:120] = (0, 255, 255)   # BGR yellow, left
    right = np.full((200, 400, 3), 255, np.uint8)
    right[80:160, 280:380] = (0, 255, 255)  # right
    rl = detect_victim(left, **VICTIM_PARAMS)
    rr = detect_victim(right, **VICTIM_PARAMS)
    assert rl['detected'] and rr['detected']
    assert rl['bearing'] < 0 < rr['bearing']


def test_dataset_has_volume():
    """Guard against the data dir going missing -- we expect many images."""
    assert len(POSITIVES) >= 14 and len(NEGATIVES) >= 18


# ---- AprilTag reading ----------------------------------------------------

TAG_IDS = [1, 2, 3, 5]


def _apriltag_detector():
    pupil = pytest.importorskip('pupil_apriltags')
    return pupil.Detector(families='tag36h11')


def _tag_path(tag_id):
    return os.path.join(DATA, 'apriltag', f'tag36h11_{tag_id}.png')


@pytest.mark.parametrize('tag_id', TAG_IDS)
def test_apriltag_read_id_upright(tag_id):
    det = _apriltag_detector()
    gray = cv2.imread(_tag_path(tag_id), cv2.IMREAD_GRAYSCALE)
    assert gray is not None
    ids = [r.tag_id for r in det.detect(gray)]
    assert tag_id in ids, f'expected to read tag {tag_id}, got {ids}'
    assert tag_id_to_box_count(tag_id) == min(tag_id, 5)


@pytest.mark.parametrize('tag_id', [2, 3])
@pytest.mark.parametrize('angle', CAMERA_ANGLES)
def test_apriltag_read_from_camera_angle(tag_id, angle):
    """Tag still reads when seen from a high/low/side angle (mild perspective;
    extreme angles clip a tag's quiet zone and are out of scope)."""
    det = _apriltag_detector()
    warped = _perspective(cv2.imread(_tag_path(tag_id)), angle, amount=0.18)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    ids = [r.tag_id for r in det.detect(gray)]
    assert tag_id in ids, f'tag {tag_id} not read from {angle}: {ids}'


@pytest.mark.parametrize('tag_id', [2, 3])
def test_apriltag_read_robust_to_rotation_exposure(tag_id):
    det = _apriltag_detector()
    bgr = cv2.imread(_tag_path(tag_id))
    rng = np.random.default_rng(7)
    trials, hits = 20, 0
    for _ in range(trials):
        aug = _random_augment(bgr, rng, max_angle=15.0, max_tilt=0.05, gain_range=(0.6, 1.4))
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
