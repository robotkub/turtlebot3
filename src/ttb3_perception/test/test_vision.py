"""Vision unit tests -- run in CI with NO ROS (OpenCV + numpy + pupil-apriltags).
They exercise the two things the vision stack must get right:

  1. AprilTag: read a tag from an image and produce the right box count,
     including when the tag is seen at an angle (perspective).
  2. Victim: detect the victim sign as a HUMAN FIGURE (a MobileNet-SSD person
     detector -- NOT colour) across many cartoon-people images (the real
     reference art + composited scenes), and NOT false-trigger on non-human
     scenes (arena, tags, blank/coloured backgrounds) -- while each image is
     randomly rotated, tilted, viewed from a camera angle, and re-exposed.

Any image under people/positive/ must be detected as a person; people/negative/
must not. Drop real photos into those folders and they're tested automatically.

The detection logic is in ttb3_perception.vision_core (ROS-free on purpose).
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
    detect_person,
    load_person_net,
    tag_id_to_box_count,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
MODELS = os.path.normpath(os.path.join(HERE, '..', 'models'))
CONF = 0.45


# ---- shared DNN net (load once) ------------------------------------------

@pytest.fixture(scope='session')
def net():
    proto = os.path.join(MODELS, 'MobileNetSSD_deploy.prototxt')
    model = os.path.join(MODELS, 'MobileNetSSD_deploy.caffemodel')
    if not (os.path.exists(proto) and os.path.exists(model)):
        pytest.skip('MobileNet-SSD model not found in models/')
    try:
        return load_person_net(proto, model)
    except AttributeError:
        pytest.skip('cv2.dnn.readNetFromCaffe unavailable (needs OpenCV < 5)')


def _images(subdir):
    paths = sorted(glob.glob(os.path.join(DATA, 'people', subdir, '*.png')))
    return [(os.path.basename(p), p) for p in paths]


POSITIVES = _images('positive')
NEGATIVES = _images('negative')


def _load(path):
    img = cv2.imread(path)
    assert img is not None, f'could not read {path}'
    return img


def _is_person(net, img):
    return detect_person(img, net, conf_threshold=CONF)['detected']


# ---- augmentation --------------------------------------------------------

def _random_augment(bgr, rng):
    """Realistic camera variation: rotation, left/right tilt, a camera angle
    (perspective), and exposure. Not 90-degree flips -- a person detector, like
    the real robot, sees the sign roughly upright."""
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 2] = np.clip(hsv[..., 2] * rng.uniform(0.6, 1.5), 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-15, 15), 1.0)
    m[0, 1] += rng.uniform(-0.1, 0.1)
    out = cv2.warpAffine(out, m, (w, h), borderValue=(255, 255, 255))

    s = rng.uniform(0, 0.14)
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = [
        np.float32([[w * s, 0], [w * (1 - s), 0], [w, h], [0, h]]),       # pitch down
        np.float32([[0, 0], [w, 0], [w * (1 - s), h], [w * s, h]]),       # pitch up
        np.float32([[0, 0], [w, h * s], [w, h * (1 - s)], [0, h]]),       # yaw
        np.float32([[0, h * s], [w, 0], [w, h], [0, h * (1 - s)]]),
    ][rng.integers(0, 4)]
    return cv2.warpPerspective(out, cv2.getPerspectiveTransform(src, dst),
                               (w, h), borderValue=(255, 255, 255))


# ---- victim = human figure -----------------------------------------------

def test_dataset_has_volume():
    assert len(POSITIVES) >= 20, f'only {len(POSITIVES)} positive images'
    assert len(NEGATIVES) >= 12, f'only {len(NEGATIVES)} negative images'


@pytest.mark.parametrize('name,path', POSITIVES)
def test_person_detected_upright(net, name, path):
    assert _is_person(net, _load(path)), f'{name}: person not detected'


@pytest.mark.parametrize('name,path', NEGATIVES)
def test_non_person_rejected_upright(net, name, path):
    assert not _is_person(net, _load(path)), f'{name}: false person detection'


def test_positives_robust_to_camera_variation(net):
    """Across ALL positive images, detection holds up under random
    rotation/tilt/camera-angle/exposure (aggregate >= 85%)."""
    rng = np.random.default_rng(7)
    total = hits = 0
    for _, path in POSITIVES:
        img = _load(path)
        for _ in range(6):
            hits += _is_person(net, _random_augment(img, rng))
            total += 1
    assert hits >= 0.85 * total, f'only {hits}/{total} detections under augmentation'


def test_negatives_no_false_positive_under_augmentation(net):
    """Non-human scenes never become a person, even augmented."""
    rng = np.random.default_rng(7)
    false_hits = 0
    for _, path in NEGATIVES:
        img = _load(path)
        for _ in range(6):
            false_hits += _is_person(net, _random_augment(img, rng))
    assert false_hits == 0, f'{false_hits} false person detections under augmentation'


def test_bearing_sign(net):
    """A person on the left gives negative bearing; on the right, positive.
    Place a whole reference figure image into the left vs right half of a wide
    white canvas (keeps the figure recognizable to the detector)."""
    ref = _load(os.path.join(DATA, 'people', 'positive', 'real_yellow_ref.png'))
    h, w = ref.shape[:2]
    canvas_w = w * 3
    left = np.full((h, canvas_w, 3), 255, np.uint8)
    left[:, 0:w] = ref
    right = np.full((h, canvas_w, 3), 255, np.uint8)
    right[:, canvas_w - w:canvas_w] = ref
    rl = detect_person(left, net, conf_threshold=CONF)
    rr = detect_person(right, net, conf_threshold=CONF)
    assert rl['detected'] and rr['detected']
    assert rl['bearing'] < 0 < rr['bearing']


# ---- AprilTag reading ----------------------------------------------------

TAG_IDS = [1, 2, 3, 5]
CAMERA_ANGLES = ['pitch_down', 'pitch_up', 'yaw_left', 'yaw_right']


def _apriltag_detector():
    pupil = pytest.importorskip('pupil_apriltags')
    return pupil.Detector(families='tag36h11')


def _tag_path(tag_id):
    return os.path.join(DATA, 'apriltag', f'tag36h11_{tag_id}.png')


def _perspective(img, kind, amount):
    h, w = img.shape[:2]
    s = amount
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = {
        'pitch_down': np.float32([[w * s, 0], [w * (1 - s), 0], [w, h], [0, h]]),
        'pitch_up': np.float32([[0, 0], [w, 0], [w * (1 - s), h], [w * s, h]]),
        'yaw_left': np.float32([[0, 0], [w, h * s], [w, h * (1 - s)], [0, h]]),
        'yaw_right': np.float32([[0, h * s], [w, 0], [w, h], [0, h * (1 - s)]]),
    }[kind]
    return cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst),
                               (w, h), borderValue=(255, 255, 255))


@pytest.mark.parametrize('tag_id', TAG_IDS)
def test_apriltag_read_id_upright(tag_id):
    det = _apriltag_detector()
    gray = cv2.imread(_tag_path(tag_id), cv2.IMREAD_GRAYSCALE)
    assert gray is not None
    ids = [r.tag_id for r in det.detect(gray)]
    assert tag_id in ids, f'expected tag {tag_id}, got {ids}'
    assert tag_id_to_box_count(tag_id) == min(tag_id, 5)


@pytest.mark.parametrize('tag_id', [2, 3])
@pytest.mark.parametrize('angle', CAMERA_ANGLES)
def test_apriltag_read_from_camera_angle(tag_id, angle):
    det = _apriltag_detector()
    warped = _perspective(cv2.imread(_tag_path(tag_id)), angle, 0.18)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    ids = [r.tag_id for r in det.detect(gray)]
    assert tag_id in ids, f'tag {tag_id} not read from {angle}: {ids}'


# ---- pure helpers --------------------------------------------------------

def test_tag_id_to_box_count_clamps():
    assert tag_id_to_box_count(3) == 3
    assert tag_id_to_box_count(9, max_count=5) == 5
    assert tag_id_to_box_count(-2) == 0
    assert tag_id_to_box_count(2, offset=1) == 3


def test_corner_area_unit_square():
    assert corner_area([(0, 0), (10, 0), (10, 10), (0, 10)]) == pytest.approx(100.0)
