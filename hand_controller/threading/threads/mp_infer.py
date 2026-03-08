from __future__ import annotations
import cv2
import queue
import threading

from ...config import DEFAULT_LABELS
from ...core.coords import frame_to_screen_xy
from ...core.labels import canonicalize_label
from ...ml.geo18 import extract_geo18
from ...threading.types import FramePacket, InferPacket
from ...vision.hand_selector import HandSelector
from ...vision.hand_tracker import HandTracker


MOVEMENT_ANCHOR_IDX = 5  # stable movement anchor: index MCP / base
VISUAL_CURSOR_IDX = 8    # visual / hit-test cursor: index fingertip


def _landmark_norm(hand_landmarks, idx: int) -> tuple[float, float]:
    lm = hand_landmarks.landmark[idx]
    return float(lm.x), float(lm.y)


def _movement_anchor_norm(hand_landmarks) -> tuple[float, float]:
    return _landmark_norm(hand_landmarks, MOVEMENT_ANCHOR_IDX)


def _visual_cursor_norm(hand_landmarks) -> tuple[float, float]:
    return _landmark_norm(hand_landmarks, VISUAL_CURSOR_IDX)


def _predict_label(mlp, hand: dict | None) -> tuple[str, float, float]:
    if mlp is None or hand is None:
        return DEFAULT_LABELS["idle"], 1.0, 1.0
    feats = extract_geo18(hand["landmarks"])
    res = mlp.predict(feats)
    return canonicalize_label(str(res.label)), float(res.p1), float(res.margin)


def _build_overlay(hands, tracker, screen_w, screen_h):
    points = []
    lines = []
    for hand in hands:
        lm = hand["landmarks"]
        cx, cy = _visual_cursor_norm(lm)
        sx, sy = frame_to_screen_xy(cx, cy, screen_w, screen_h)
        points.append({"label": hand["label"], "x": sx, "y": sy})
        for a, b in tracker.connections:
            la, lb = lm.landmark[a], lm.landmark[b]
            x1, y1 = frame_to_screen_xy(la.x, la.y, screen_w, screen_h)
            x2, y2 = frame_to_screen_xy(lb.x, lb.y, screen_w, screen_h)
            lines.append((x1, y1, x2, y2))
    return points, lines


def _movement_cursor_for(hand):
    if hand is None:
        return None
    cx, cy = _movement_anchor_norm(hand["landmarks"])
    return (cx, cy)


def _visual_cursor_for(hand, screen_w, screen_h):
    if hand is None:
        return None
    cx, cy = _visual_cursor_norm(hand["landmarks"])
    return frame_to_screen_xy(cx, cy, screen_w, screen_h)


def infer_loop(stop: threading.Event, in_q: queue.Queue, out_q: queue.Queue, mlp, screen_w: int, screen_h: int):
    tracker = HandTracker(max_num_hands=2)
    selector = HandSelector()
    try:
        while not stop.is_set():
            try:
                pkt: FramePacket = in_q.get(timeout=0.1)
            except queue.Empty:
                continue

            frame = cv2.flip(pkt.frame_bgr, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = tracker.process(rgb)
            hands = tracker.extract_hands(result)
            frame_h, frame_w = frame.shape[:2]
            selected = selector.select(hands, frame.shape)

            active_hand_present = selected.primary is not None
            secondary_hand_present = selected.secondary is not None
            active_hand_label = selected.primary.get("label") if selected.primary else None

            active_cursor_norm = _movement_cursor_for(selected.primary)
            active_cursor_screen = _visual_cursor_for(selected.primary, screen_w, screen_h)
            left_cursor_screen = _visual_cursor_for(selected.left, screen_w, screen_h)
            right_cursor_screen = _visual_cursor_for(selected.right, screen_w, screen_h)

            primary_label, p1, margin = _predict_label(mlp, selected.primary)
            secondary_label, _, _ = _predict_label(mlp, selected.secondary)
            left_label, _, _ = _predict_label(mlp, selected.left)
            right_label, _, _ = _predict_label(mlp, selected.right)

            overlay_points, overlay_lines = _build_overlay(hands, tracker, screen_w, screen_h)
            preview = cv2.resize(frame, (320, 240))
            out = InferPacket(
                t_capture=pkt.t_capture,
                frame_w=frame_w,
                frame_h=frame_h,
                active_hand_present=active_hand_present,
                active_hand_label=active_hand_label,
                active_cursor_norm=active_cursor_norm,
                active_cursor_screen=active_cursor_screen,
                secondary_hand_present=secondary_hand_present,
                keyboard_left_present=selected.left is not None,
                keyboard_left_label=selected.left.get("label") if selected.left else None,
                keyboard_left_cursor_screen=left_cursor_screen,
                keyboard_left_prediction=left_label if selected.left else None,
                keyboard_right_present=selected.right is not None,
                keyboard_right_label=selected.right.get("label") if selected.right else None,
                keyboard_right_cursor_screen=right_cursor_screen,
                keyboard_right_prediction=right_label if selected.right else None,
                primary_prediction=primary_label,
                secondary_prediction=secondary_label if secondary_hand_present else None,
                label=primary_label,
                p1=p1,
                margin=margin,
                overlay_points=overlay_points,
                overlay_lines=overlay_lines,
                preview_frame=preview,
            )
            while out_q.full():
                try:
                    out_q.get_nowait()
                except queue.Empty:
                    break
            out_q.put(out)
    finally:
        tracker.close()
