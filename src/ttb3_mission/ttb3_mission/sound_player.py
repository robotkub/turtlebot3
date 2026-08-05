#!/usr/bin/env python3
"""Speaks the mission out loud: one wav per notable moment.

Runs ON THE PI, started by hardware.launch.py, and that is deliberate.

Audio cannot come out of the laptop container. Docker Desktop on macOS has
no /dev/snd to pass through -- the containers live in a Linux VM with no
sound device at all -- so `--device /dev/snd` simply has nothing to bind.
The only route from a container on a Mac is streaming to a PulseAudio server
on the host over TCP, which means installing and configuring PulseAudio on
every teammate's laptop. Meanwhile the Pi already has a real card (bcm2835
Headphones, the 3.5 mm jack) and runs its nodes natively with no Docker in
the way. It is also the right answer on the merits: the robot should be the
thing that makes the noise, so judges and bystanders hear it rather than
whoever happens to be holding the laptop.

Because it listens to /mission_event on the shared graph, it does not care
that mission_manager is running on the laptop.

Plug a speaker into the Pi's 3.5 mm jack. Set the output and volume with:
    amixer -c 0 sset Headphone 90%
"""
import os
import queue
import threading
import wave

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# Event name -> file in the sounds directory. Event names are published by
# mission_manager; anything not listed here is ignored (with a log line) so a
# new event can't crash the player.
SOUNDS = {
    'mission_start': 'start-mission-count-down.wav',
    'next_zone': 'next-destination-announce.wav',
    'zone_reached': 'reach-the-destination-point.wav',
    'object_detected': 'object-detected.wav',
    'dispense': 'activate-dispencer.wav',
    'estop': 'estop-activate.wav',
    'mission_done': 'mission-done.wav',
}


def _default_sound_dir():
    return os.path.expanduser('~/turtlebot3_ws/assets/sound')


class SoundPlayer(Node):

    def __init__(self):
        super().__init__('sound_player')
        self.declare_parameter('sound_dir', _default_sound_dir())
        self.declare_parameter('enabled', True)
        self._dir = self.get_parameter('sound_dir').value
        self._enabled = self.get_parameter('enabled').value

        # Play on a worker thread. Playback is seconds long and blocking it on
        # the executor would stall every other callback in this process --
        # including, on the Pi, the ones driving hardware.
        self._q = queue.Queue(maxsize=8)
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

        self.create_subscription(String, '/mission_event', self._on_event, 10)

        missing = [f for f in SOUNDS.values()
                   if not os.path.isfile(os.path.join(self._dir, f))]
        if missing:
            self.get_logger().warning(
                f'sound_dir {self._dir} is missing {len(missing)} file(s): '
                f'{", ".join(sorted(missing))}')
        self.get_logger().info(
            f'sound_player ready (dir={self._dir}, enabled={self._enabled})')

    def _on_event(self, msg: String):
        name = msg.data.strip()
        f = SOUNDS.get(name)
        if f is None:
            self.get_logger().info(f'no sound mapped for event {name!r}')
            return
        if not self._enabled:
            return
        try:
            self._q.put_nowait(os.path.join(self._dir, f))
        except queue.Full:
            # Better to drop an announcement than to queue up a backlog that
            # plays long after the moment it describes.
            self.get_logger().warning(f'sound queue full, dropped {name}')

    def _run(self):
        while not self._stop.is_set():
            try:
                path = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._play(path)
            except Exception as exc:            # noqa: BLE001
                # Audio must never take the mission down: a missing file, an
                # unplugged card or a busy device is a lost announcement, not
                # a failure worth propagating.
                self.get_logger().warning(f'could not play {path}: {exc}')

    def _play(self, path):
        import pyaudio  # imported lazily so a machine with no audio still runs
        with wave.open(path, 'rb') as wf:
            pa = pyaudio.PyAudio()
            try:
                stream = pa.open(
                    format=pa.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)
                try:
                    data = wf.readframes(1024)
                    while data and not self._stop.is_set():
                        stream.write(data)
                        data = wf.readframes(1024)
                finally:
                    stream.stop_stream()
                    stream.close()
            finally:
                pa.terminate()

    def destroy_node(self):
        self._stop.set()
        self._worker.join(timeout=2.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SoundPlayer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
