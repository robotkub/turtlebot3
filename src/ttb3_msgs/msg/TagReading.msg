# Simplified AprilTag result published by apriltag_detector on /tag_detections.
# Decodes the raw apriltag_ros detection into what mission_manager actually
# needs: is there a valid tag right now, and how many boxes does it mean.
bool valid
int32 tag_id
int32 box_count
