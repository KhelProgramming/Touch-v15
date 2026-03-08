from __future__ import annotations
import queue
import threading
import time

from ...interaction.interaction_engine import InteractionEngine
from ..types import ActionPacket, InferPacket


def logic_loop(stop: threading.Event, in_q: queue.Queue, out_q: queue.Queue, screen_w: int, screen_h: int):
    engine = InteractionEngine(screen_w, screen_h)

    while not stop.is_set():
        try:
            pkt: InferPacket = in_q.get(timeout=0.1)
        except queue.Empty:
            continue

        actions, mode, overlay = engine.update(pkt, now=time.time())

        # Keep everything the UI may need
        overlay_state = dict(overlay or {})
        overlay_state.update(
            {
                "mode": mode,
                "gesture": pkt.label,
                "gesture_label": pkt.label,
                "confidence": pkt.p1,
                "margin": pkt.margin,

                # Camera preview
                "preview_frame": pkt.preview_frame,

                # Skeleton / landmark style overlay info
                "overlay_points": pkt.overlay_points,
                "overlay_lines": pkt.overlay_lines,

                # Mouse / active hand info
                "active_hand_present": pkt.active_hand_present,
                "active_hand_label": pkt.active_hand_label,
                "active_cursor_screen": pkt.active_cursor_screen,

                # Keyboard hand info
                "keyboard_left_present": pkt.keyboard_left_present,
                "keyboard_left_label": pkt.keyboard_left_label,
                "keyboard_left_cursor_screen": pkt.keyboard_left_cursor_screen,
                "keyboard_left_prediction": pkt.keyboard_left_prediction,

                "keyboard_right_present": pkt.keyboard_right_present,
                "keyboard_right_label": pkt.keyboard_right_label,
                "keyboard_right_cursor_screen": pkt.keyboard_right_cursor_screen,
                "keyboard_right_prediction": pkt.keyboard_right_prediction,
            }
        )

        out = ActionPacket(
            t_capture=pkt.t_capture,
            mode=mode,
            actions=actions,
            overlay_state=overlay_state,
        )

        while out_q.full():
            try:
                out_q.get_nowait()
            except queue.Empty:
                break

        out_q.put(out)