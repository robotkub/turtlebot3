#!/usr/bin/env python3
"""Continuously saves the SLAM map so you never lose it.

Subscribes /map and writes <map_path>.pgm + <map_path>.yaml every N seconds AND
once more on shutdown (Ctrl-C). That means you just drive the robot around, then
kill the mapping launch -- the latest map is already on disk at map_path, no
separate "save" step. Replaces the old 3_map_save.sh.

Pure Python OccupancyGrid -> PGM (P5) writer, so it has no dependency on
nav2_map_server's map_saver. Output format matches what Nav2's map_server loads.
"""
import os

import rclpy
import yaml
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy


class MapAutosaver(Node):

    def __init__(self):
        super().__init__('map_autosaver')
        self.declare_parameter('map_path', os.path.join(os.getcwd(), 'map_autosave'))
        self.declare_parameter('save_period_sec', 15.0)
        self.declare_parameter('occupied_thresh', 0.65)
        self.declare_parameter('free_thresh', 0.25)

        self._map_path = os.path.expanduser(self.get_parameter('map_path').value)
        os.makedirs(os.path.dirname(os.path.abspath(self._map_path)), exist_ok=True)
        self._latest = None

        # SLAM publishes /map with TRANSIENT_LOCAL (latched); match it so we
        # receive the last map even if we start after the mapper.
        qos = QoSProfile(
            depth=1,
            history=QoSHistoryPolicy.KEEP_LAST,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(OccupancyGrid, '/map', self._on_map, qos)
        self.create_timer(self.get_parameter('save_period_sec').value, self._on_timer)
        self.get_logger().info(
            f'map_autosaver: will save to {self._map_path}.pgm/.yaml '
            f'every {self.get_parameter("save_period_sec").value:.0f}s and on exit')

    def _on_map(self, msg: OccupancyGrid):
        self._latest = msg

    def _on_timer(self):
        self.save()

    def save(self):
        if self._latest is None:
            return
        grid = self._latest
        w, h = grid.info.width, grid.info.height
        res = grid.info.resolution
        ox, oy = grid.info.origin.position.x, grid.info.origin.position.y

        pgm = self._map_path + '.pgm'
        yml = self._map_path + '.yaml'

        # OccupancyGrid: -1 unknown, 0 free .. 100 occupied. Map to the standard
        # map_server PGM greyscale: 254 free, 000 occupied, 205 unknown. Rows are
        # bottom-up in the grid but top-down in the image, so flip vertically.
        pixels = bytearray(w * h)
        data = grid.data
        for row in range(h):
            src = (h - 1 - row) * w
            dst = row * w
            for col in range(w):
                v = data[src + col]
                if v < 0:
                    pixels[dst + col] = 205
                elif v >= 65:
                    pixels[dst + col] = 0
                elif v <= 25:
                    pixels[dst + col] = 254
                else:
                    pixels[dst + col] = 205
        with open(pgm, 'wb') as f:
            f.write(f'P5\n{w} {h}\n255\n'.encode('ascii'))
            f.write(bytes(pixels))

        with open(yml, 'w') as f:
            yaml.safe_dump({
                'image': os.path.basename(pgm),
                'mode': 'trinary',
                'resolution': float(res),
                'origin': [float(ox), float(oy), 0.0],
                'negate': 0,
                'occupied_thresh': float(self.get_parameter('occupied_thresh').value),
                'free_thresh': float(self.get_parameter('free_thresh').value),
            }, f, default_flow_style=False, sort_keys=False)
        self.get_logger().info(f'saved map ({w}x{h} @ {res:.3f} m/px) -> {pgm}')


def main():
    rclpy.init()
    node = MapAutosaver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Final save so killing the launch always leaves the latest map on disk.
        node.get_logger().info('shutting down -- final map save')
        node.save()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
