#!/usr/bin/env python3
"""Generate the person-detection test dataset by compositing the real cartoon
figures (real_*.png, the reference victim-sign art) onto many different
backgrounds at varied scale/position/rotation/exposure. Produces:

  people/positive/comp_*.png  -- a cartoon human somewhere in the scene
  people/negative/bg_*.png    -- the same kinds of background but NO person

Why composite instead of downloading: clean, license-safe (derived from the
reference art), and every generated scene is verified against the DNN person
detector before being kept, so the committed set is deterministic and CI is
never flaky. Real photos dropped into people/positive|negative are picked up by
the tests too.

    python3 generate_people_dataset.py    # regenerate

Requires the model in ../../models/ and opencv<5 (readNetFromCaffe)."""
import glob
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(HERE, 'people', 'positive')
NEG = os.path.join(HERE, 'people', 'negative')
MODELS = os.path.normpath(os.path.join(HERE, '..', '..', 'models'))
PERSON_CLASS = 15


def load_net():
    return cv2.dnn.readNetFromCaffe(
        os.path.join(MODELS, 'MobileNetSSD_deploy.prototxt'),
        os.path.join(MODELS, 'MobileNetSSD_deploy.caffemodel'))


def person_conf(net, bgr):
    net.setInput(cv2.dnn.blobFromImage(bgr, 0.007843, (300, 300), 127.5))
    det = net.forward()
    return max((float(det[0, 0, i, 2]) for i in range(det.shape[2])
                if int(det[0, 0, i, 1]) == PERSON_CLASS), default=0.0)


def cutout(bgr):
    """Alpha-cut the figure off its near-white background."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mask = (gray < 245).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return bgr, np.full(gray.shape, 255, np.uint8)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    return bgr[y0:y1 + 1, x0:x1 + 1], mask[y0:y1 + 1, x0:x1 + 1]


def make_background(rng, w=500, h=400, arena=None):
    kind = rng.integers(0, 4)
    if kind == 0:  # solid
        c = tuple(int(v) for v in rng.integers(60, 230, 3))
        return np.full((h, w, 3), c, np.uint8)
    if kind == 1:  # vertical gradient
        top = rng.integers(40, 200, 3).astype(np.float32)
        bot = rng.integers(40, 220, 3).astype(np.float32)
        t = np.linspace(0, 1, h)[:, None, None]
        return (top * (1 - t) + bot * t).astype(np.uint8) * np.ones((1, w, 1), np.uint8)
    if kind == 2 and arena is not None:  # arena texture crop
        ah, aw = arena.shape[:2]
        y = int(rng.integers(0, max(1, ah - h))); x = int(rng.integers(0, max(1, aw - w)))
        return cv2.resize(arena[y:y + h, x:x + w], (w, h))
    return np.clip(rng.normal(150, 40, (h, w, 3)), 0, 255).astype(np.uint8)  # noise


def expose(bgr, rng):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 2] = np.clip(hsv[..., 2] * rng.uniform(0.6, 1.5), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def paste(bg, fig, mask, rng):
    H, W = bg.shape[:2]
    scale = rng.uniform(0.45, 0.9) * H / fig.shape[0]
    fw, fh = max(1, int(fig.shape[1] * scale)), max(1, int(fig.shape[0] * scale))
    fig_r = cv2.resize(fig, (fw, fh)); m_r = cv2.resize(mask, (fw, fh))
    # slight rotation
    ang = rng.uniform(-12, 12)
    M = cv2.getRotationMatrix2D((fw / 2, fh / 2), ang, 1.0)
    fig_r = cv2.warpAffine(fig_r, M, (fw, fh), borderValue=(0, 0, 0))
    m_r = cv2.warpAffine(m_r, M, (fw, fh), borderValue=0)
    x = int(rng.integers(0, max(1, W - fw))); y = int(rng.integers(0, max(1, H - fh)))
    out = bg.copy()
    roi = out[y:y + fh, x:x + fw]
    a = (m_r > 127)[..., None]
    out[y:y + fh, x:x + fw] = np.where(a, fig_r, roi)
    return out


def main():
    os.makedirs(POS, exist_ok=True)
    os.makedirs(NEG, exist_ok=True)
    net = load_net()
    rng = np.random.default_rng(20260801)
    arena_path = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..',
                                               'assets', 'arena', 'arena-layout.png'))
    arena = cv2.imread(arena_path)

    figures = []
    for p in sorted(glob.glob(os.path.join(POS, 'real_*.png'))):
        fig, mask = cutout(cv2.imread(p))
        figures.append((os.path.basename(p), fig, mask))

    # positives: figure composited onto a background, kept only if DNN detects it
    made = 0
    for i in range(40):
        if made >= 20:
            break
        name, fig, mask = figures[i % len(figures)]
        scene = expose(paste(make_background(rng, arena=arena), fig, mask, rng), rng)
        if person_conf(net, scene) > 0.45:
            cv2.imwrite(os.path.join(POS, f'comp_{made:02d}.png'), scene)
            made += 1
    print(f'positives: {len(figures)} real + {made} composited')

    # negatives: the same background kinds with NO person + a couple of props
    nn = 0
    for i in range(14):
        scene = expose(make_background(rng, arena=arena), rng)
        if person_conf(net, scene) <= 0.45:
            cv2.imwrite(os.path.join(NEG, f'bg_{nn:02d}.png'), scene)
            nn += 1
    # arena crops + a tag + a colored block
    if arena is not None:
        for j, (y, x) in enumerate([(150, 250), (500, 600), (700, 200)]):
            crop = arena[y:y + 400, x:x + 500]
            if crop.size and person_conf(net, crop) <= 0.45:
                cv2.imwrite(os.path.join(NEG, f'arena_{j}.png'), crop)
    tag = cv2.imread(os.path.join(HERE, 'apriltag', 'tag36h11_3.png'))
    if tag is not None:
        cv2.imwrite(os.path.join(NEG, 'tag.png'), tag)
    block = np.full((400, 500, 3), 255, np.uint8)
    cv2.rectangle(block, (120, 100), (380, 300), (0, 210, 255), -1)
    cv2.imwrite(os.path.join(NEG, 'block.png'), block)
    print(f'negatives: {len(glob.glob(os.path.join(NEG, "*.png")))}')


if __name__ == '__main__':
    main()
