from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math
import time

from ..config import SelectorSettings
from ..core.coords import bbox_area


@dataclass(slots=True)
class SelectedHands:
    primary: dict[str, Any] | None
    secondary: dict[str, Any] | None
    left: dict[str, Any] | None
    right: dict[str, Any] | None


class HandSelector:
    def __init__(self, settings: SelectorSettings | None = None):
        self.settings = settings or SelectorSettings()
        self._last_mouse_center: tuple[float, float] | None = None
        self._last_seen_time: float = 0.0

    def _score(self, hand: dict[str, Any], frame_shape) -> float:
        h, w = frame_shape[:2]
        return bbox_area(hand["landmarks"], w, h)

    def _center_px(self, hand: dict[str, Any], frame_shape) -> tuple[float, float]:
        h, w = frame_shape[:2]
        lm = hand["landmarks"].landmark[5]  # index MCP / base
        return (lm.x * w, lm.y * h)

    def select(self, hands: list[dict[str, Any]], frame_shape) -> SelectedHands:
        now = time.time()
        if not hands:
            if now - self._last_seen_time > self.settings.lost_grace_seconds:
                self._last_mouse_center = None
            return SelectedHands(primary=None, secondary=None, left=None, right=None)

        scored = [(self._score(h, frame_shape), h) for h in hands]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_hand = scored[0]
        chosen = best_hand

        if self._last_mouse_center is not None:
            best_dist = math.inf
            best_match = None
            for score, hand in scored:
                cx, cy = self._center_px(hand, frame_shape)
                dist = math.hypot(cx - self._last_mouse_center[0], cy - self._last_mouse_center[1])
                if dist < best_dist:
                    best_dist = dist
                    best_match = (score, hand)
            if best_match is not None and best_dist <= self.settings.centroid_switch_px:
                match_score, match_hand = best_match
                if match_score >= best_score * (1.0 - self.settings.switch_margin):
                    chosen = match_hand

        self._last_mouse_center = self._center_px(chosen, frame_shape)
        self._last_seen_time = now

        secondary = None
        for _, hand in scored:
            if hand is not chosen:
                secondary = hand
                break

        left = None
        right = None
        for _, hand in scored:
            label = str(hand.get("label", "")).lower()
            if label == 'left' and left is None:
                left = hand
            elif label == 'right' and right is None:
                right = hand

        return SelectedHands(primary=chosen, secondary=secondary, left=left, right=right)
