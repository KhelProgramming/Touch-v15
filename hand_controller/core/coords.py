from __future__ import annotations
import math
from typing import Iterable, Tuple


def frame_to_screen_xy(norm_x: float, norm_y: float, screen_w: int, screen_h: int) -> tuple[int, int]:
    return int(norm_x * screen_w), int(norm_y * screen_h)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def landmark_pixel(hand_landmarks, frame_w: int, frame_h: int, idx: int) -> tuple[int, int]:
    lm = hand_landmarks.landmark[idx]
    return int(lm.x * frame_w), int(lm.y * frame_h)


def bbox_from_landmarks(hand_landmarks, frame_w: int, frame_h: int) -> tuple[int, int, int, int]:
    xs = [lm.x * frame_w for lm in hand_landmarks.landmark]
    ys = [lm.y * frame_h for lm in hand_landmarks.landmark]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def bbox_area(hand_landmarks, frame_w: int, frame_h: int) -> float:
    x1, y1, x2, y2 = bbox_from_landmarks(hand_landmarks, frame_w, frame_h)
    return float(max(1, x2 - x1) * max(1, y2 - y1))


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])
