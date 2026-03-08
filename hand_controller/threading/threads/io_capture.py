from __future__ import annotations
import queue
import threading
import time

from ...vision.camera import Camera
from ..types import FramePacket


def io_capture_loop(stop: threading.Event, out_q: queue.Queue, cam_index: int, width: int, height: int):
    cam = Camera(index=cam_index, width=width, height=height)
    for _ in range(12):
        cam.read()
    try:
        while not stop.is_set():
            tcap = time.time()
            ret, frame = cam.read()
            if not ret:
                continue
            pkt = FramePacket(t_capture=tcap, frame_bgr=frame)
            while out_q.full():
                try:
                    out_q.get_nowait()
                except queue.Empty:
                    break
            out_q.put(pkt)
    finally:
        cam.release()
