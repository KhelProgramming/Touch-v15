from __future__ import annotations
import queue
import threading
import time

from ...controllers.action_executor import execute_actions
from ..types import ActionPacket


def exec_loop(
    stop: threading.Event,
    in_q: queue.Queue,
    overlay_bus=None,
    metrics: dict | None = None,
):
    metrics = metrics if metrics is not None else {
        "actions_completed": 0,
        "total_latency_ms": 0.0,
    }

    last_fps_time = time.time()
    fps_counter = 0
    current_fps = 0.0

    while not stop.is_set():
        try:
            pkt: ActionPacket = in_q.get(timeout=0.1)
        except queue.Empty:
            continue

        # -----------------------------
        # Execute actions
        # -----------------------------
        if pkt.actions:
            execute_actions(pkt.actions)
            metrics["actions_completed"] += len(pkt.actions)

        latency_ms = (time.time() - pkt.t_capture) * 1000.0
        metrics["total_latency_ms"] += latency_ms

        # -----------------------------
        # FPS estimation for UI
        # -----------------------------
        fps_counter += 1
        now = time.time()
        elapsed = now - last_fps_time
        if elapsed >= 1.0:
            current_fps = fps_counter / elapsed
            fps_counter = 0
            last_fps_time = now

        # -----------------------------
        # Emit overlay payload
        # -----------------------------
        if overlay_bus is not None:
            try:
                payload = dict(pkt.overlay_state or {})

                # normalize common UI fields
                payload.setdefault("mode", pkt.mode)
                payload.setdefault("fps", current_fps)
                payload.setdefault("latency_ms", latency_ms)

                # keep these keys if they already exist in overlay_state:
                # gesture / confidence / left_hover / right_hover /
                # left_pressed / right_pressed / frame_bgr / preview_frame

                overlay_bus.update_overlay.emit(payload)
            except Exception:
                pass