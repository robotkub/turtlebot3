← [4. Understanding Navigation](04-navigation.md) | [Back to index](00-index.md) | Next: [6. Running the real mission →](06-run-mission.md)

# 5. Understanding Vision

The robot needs to see two things: **the number on the AprilTag** (how many
boxes to drop) and **the victim sign** (the human-shaped sign it has to stand
in front of before dispensing).

## Basic vocabulary

| Term | Plain-English meaning |
|---|---|
| `/image_raw` | The raw camera feed, frame by frame |
| `/image_raw/compressed` | The same feed, JPEG-compressed -- used over WiFi so it doesn't eat bandwidth |
| `/camera_info` | The camera's calibration data (lens distortion etc.) |
| AprilTag | A black-and-white barcode-like marker a camera can read reliably even at an angle |

## AprilTag -- reading the number (R2, R3)

We didn't write a detector from scratch -- we use the off-the-shelf
`apriltag_ros` (already installed via apt) and wrap a thin layer around it:

```
camera --/image_raw--> apriltag_ros (apriltag_node) --/apriltag/detections--> apriltag_detector (ours) --/tag_detections--> mission_manager
```

`apriltag_detector` (`src/ttb3_perception/ttb3_perception/apriltag_detector.py`) just:
- Picks the closest tag (largest area in frame) if more than one is visible
- Converts **tag ID directly into box_count** (tag #3 = drop 3 boxes; the offset/max are adjustable params)
- Publishes `valid: false` if no tag has been seen recently

**What actually needs tuning**: `src/ttb3_perception/config/tags_36h11.yaml` -> `size:`
(the tag's black-square edge length in meters -- measure the real printed tag
and set this correctly; it affects pose accuracy, not ID reading)

## Victim detector -- finding the human-shaped sign (R4)

This team chose **color detection** (not a second AprilTag) -- using OpenCV:

1. Convert the image from BGR to HSV (separates color from brightness, making color thresholds easier)
2. Keep only pixels within a chosen color range (`hsv_lower`/`hsv_upper`)
3. Find contours (color-blob boundaries), keep the largest one above `min_contour_area`
4. Compute:
   - `bearing`: the blob's center vs. the image's center (left/right) -- used to steer toward it
   - `apparent_size`: blob area / total image area -- used as a distance proxy (bigger = closer)

Code: `src/ttb3_perception/ttb3_perception/victim_detector.py`

**What actually needs tuning**: `src/ttb3_perception/config/victim_color.yaml`

The defaults target the **yellow** victim sign (the figures wear yellow). Once
you can test under the real venue lighting:
1. Open `/image_raw` in Foxglove and look at its actual color
2. Sample a pixel's color on the sign (hover for RGB, or use any RGB->HSV converter online)
3. Update `hsv_lower`/`hsv_upper` in the config, then rebuild/restart the node

## How mission_manager uses this

During the `APPROACH_VICTIM` state, `bearing`/`apparent_size` drive `/cmd_vel`
directly (no Nav2 goal needed) -- turning toward the sign and driving closer
until `apparent_size` hits the target (`approach_close_size`) and it's
centered enough (`approach_center_tolerance`), then stopping and dispensing.
Tune these in `config/mission_params.yaml`.

## Try it yourself

1. Launch debug mode and watch `/image_raw` in Foxglove
2. Try publishing a fake `/apriltag/detections` with `ros2 topic pub` and check `apriltag_detector` converts it to the right `box_count`
3. Try changing `hsv_lower`/`hsv_upper` to a different color and restarting `victim_detector` to see the effect

Ready? Move on to [Chapter 6: Running the real mission](06-run-mission.md).

---
← [4. Understanding Navigation](04-navigation.md) | [Back to index](00-index.md) | Next: [6. Running the real mission →](06-run-mission.md)
