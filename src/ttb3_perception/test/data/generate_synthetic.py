#!/usr/bin/env python3
"""Generate synthetic 'person with a colored shirt' test images for the victim
detector. Yellow shirt -> positive (victim), any other color -> negative.

These are simple, controllable figures (no copyright concerns) that let the
vision tests run on many cases. Re-run to regenerate:

    python3 generate_synthetic.py

Real photos dropped into victim/ are picked up by the tests too -- these just
add volume and known-color ground truth. Deterministic (fixed seed)."""
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'victim', 'synthetic')

# BGR colors. Yellow is the victim sign; everything else is a distractor.
YELLOW = (0, 255, 255)
NEG_COLORS = {
    'blue': (200, 60, 20),
    'green': (40, 160, 40),
    'red': (40, 40, 200),
    'purple': (140, 40, 120),
    'cyan': (200, 200, 20),
    'orange': (20, 120, 230),   # near yellow but hue is orange -> must NOT trigger
}
SKIN = (150, 190, 230)
DARK = (60, 60, 60)


def draw_person(canvas, cx, cy, scale, shirt_bgr):
    """Draw a simple head+torso+arms+legs figure centered around (cx, cy)."""
    s = scale
    # head
    cv2.circle(canvas, (cx, int(cy - 2.2 * s)), int(0.8 * s), SKIN, -1)
    # torso (shirt)
    cv2.rectangle(canvas, (int(cx - 1.1 * s), int(cy - 1.3 * s)),
                  (int(cx + 1.1 * s), int(cy + 0.9 * s)), shirt_bgr, -1)
    # arms
    cv2.rectangle(canvas, (int(cx - 1.7 * s), int(cy - 1.2 * s)),
                  (int(cx - 1.1 * s), int(cy + 0.5 * s)), shirt_bgr, -1)
    cv2.rectangle(canvas, (int(cx + 1.1 * s), int(cy - 1.2 * s)),
                  (int(cx + 1.7 * s), int(cy + 0.5 * s)), shirt_bgr, -1)
    # legs
    cv2.rectangle(canvas, (int(cx - 0.9 * s), int(cy + 0.9 * s)),
                  (int(cx - 0.1 * s), int(cy + 3.0 * s)), DARK, -1)
    cv2.rectangle(canvas, (int(cx + 0.1 * s), int(cy + 0.9 * s)),
                  (int(cx + 0.9 * s), int(cy + 3.0 * s)), DARK, -1)


def make_image(shirt_bgr, rng):
    h, w = 300, 400
    canvas = np.full((h, w, 3), 255, np.uint8)
    scale = rng.integers(28, 42)
    cx = int(rng.integers(int(2 * scale), int(w - 2 * scale)))
    cy = int(rng.integers(int(2.5 * scale), int(h - 3 * scale)))
    draw_person(canvas, cx, cy, scale, shirt_bgr)
    return canvas


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(20260801)
    # positives: several yellow figures at random poses
    for i in range(12):
        cv2.imwrite(os.path.join(OUT, f'pos_yellow_{i:02d}.png'), make_image(YELLOW, rng))
    # negatives: distractors of every other color
    n = 0
    for name, col in NEG_COLORS.items():
        for k in range(3):
            cv2.imwrite(os.path.join(OUT, f'neg_{name}_{k}.png'), make_image(col, rng))
            n += 1
    print(f'wrote 12 yellow positives + {n} non-yellow negatives to {OUT}')


if __name__ == '__main__':
    main()
