from __future__ import annotations
from collections import Counter, deque
from dataclasses import dataclass, field
from math import hypot
from typing import List

from ..config import KeyboardSettings
from .actions import Action, KeyPress


KEYBOARD_WINDOW_W = 1420
KEYBOARD_WINDOW_H = 470
KEY_START_Y = 58
KEY_GAP = 16
KEY_ROW_GAP = 20
UNIT_W = 92
KEY_H = 64
SPECIAL_KEY_MAP = {
    "ESC": "esc",
    "ENTER": "enter",
    "SPACE": "space",
    "CAPS": "capslock",
}
KEY_HIT_PAD_X = 18
KEY_HIT_PAD_Y = 14
KEY_SNAP_RADIUS = 88.0

KEY_LAYOUT_SPEC = [
    [("ESC", 1.5), ("Q", 1.0), ("W", 1.0), ("E", 1.0), ("R", 1.0), ("T", 1.0), ("Y", 1.0), ("U", 1.0), ("I", 1.0), ("O", 1.0), ("P", 1.0)],
    [("CAPS", 2.0), ("A", 1.0), ("S", 1.0), ("D", 1.0), ("F", 1.0), ("G", 1.0), ("H", 1.0), ("J", 1.0), ("K", 1.0), ("L", 1.0), ("ENTER", 2.0)],
    [("Z", 1.0), ("X", 1.0), ("C", 1.0), ("V", 1.0), ("B", 1.0), ("N", 1.0), ("M", 1.0)],
    [("SPACE", 6.0)],
]


@dataclass(frozen=True, slots=True)
class KeyRect:
    label: str
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2.0

    def contains(self, x: int, y: int, pad_x: int = 0, pad_y: int = 0) -> bool:
        return (
            (self.x1 - pad_x) <= x <= (self.x2 + pad_x)
            and (self.y1 - pad_y) <= y <= (self.y2 + pad_y)
        )


@dataclass(slots=True)
class RepeatState:
    hover_queue: deque = field(default_factory=lambda: deque(maxlen=7))
    active: bool = False
    repeat_key: str | None = None
    repeat_kind: str | None = None
    repeat_started_at: float = 0.0
    last_repeat_time: float = 0.0


@dataclass(slots=True)
class KeyboardState:
    left: RepeatState = field(default_factory=RepeatState)
    right: RepeatState = field(default_factory=RepeatState)
    last_press_time: float = 0.0
    caps_on: bool = False


class KeyboardController:
    def __init__(self, screen_w: int, screen_h: int, settings: KeyboardSettings | None = None):
        self.settings = settings or KeyboardSettings()
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.layout = self._build_layout()
        self.state = KeyboardState()
        self.state.left.hover_queue = deque(maxlen=self.settings.hover_window)
        self.state.right.hover_queue = deque(maxlen=self.settings.hover_window)

    def _build_layout(self) -> list[KeyRect]:
        window_x = (self.screen_w - KEYBOARD_WINDOW_W) // 2
        window_y = self.screen_h - KEYBOARD_WINDOW_H - 70

        rects: list[KeyRect] = []
        for row_idx, row in enumerate(KEY_LAYOUT_SPEC):
            row_width = int(sum(units * UNIT_W for _, units in row) + KEY_GAP * (len(row) - 1))
            offset_x = (KEYBOARD_WINDOW_W - row_width) // 2
            y = window_y + KEY_START_Y + row_idx * (KEY_H + KEY_ROW_GAP)
            cursor_x = window_x + offset_x
            for key, units in row:
                w = int(round(units * UNIT_W))
                rects.append(KeyRect(key, cursor_x, y, cursor_x + w, y + KEY_H))
                cursor_x += w + KEY_GAP
        return rects

    def _snapped_key(self, x: int, y: int) -> str | None:
        nearest: KeyRect | None = None
        nearest_dist = float("inf")
        for rect in self.layout:
            dist = hypot(x - rect.cx, y - rect.cy)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = rect
        if nearest is not None and nearest_dist <= KEY_SNAP_RADIUS:
            return nearest.label
        return None

    def hovered_key(self, cursor_screen: tuple[int, int] | None) -> str | None:
        if cursor_screen is None:
            return None

        x, y = cursor_screen

        snapped = self._snapped_key(x, y)
        if snapped is not None:
            return snapped

        for rect in self.layout:
            if rect.contains(x, y):
                return rect.label

        for rect in self.layout:
            if rect.contains(x, y, pad_x=KEY_HIT_PAD_X, pad_y=KEY_HIT_PAD_Y):
                return rect.label

        return None

    def _majority_hover(self, hover_queue: deque) -> str | None:
        valid = [k for k in hover_queue if k is not None]
        if not valid:
            return None
        return Counter(valid).most_common(1)[0][0]

    def _format_key_output(self, key: str) -> str:
        mapped = SPECIAL_KEY_MAP.get(key.upper())
        if mapped is not None:
            return mapped
        if len(key) == 1 and key.isalpha():
            return key.upper() if self.state.caps_on else key.lower()
        return key.lower()

    def _apply_special_toggle(self, key: str) -> bool:
        if key.upper() == "CAPS":
            self.state.caps_on = not self.state.caps_on
            return True
        return False

    def _reset_repeat(self, state: RepeatState) -> None:
        state.repeat_key = None
        state.repeat_kind = None
        state.repeat_started_at = 0.0
        state.last_repeat_time = 0.0

    def _begin_repeat(self, state: RepeatState, kind: str, key: str, now: float) -> None:
        state.repeat_kind = kind
        state.repeat_key = key
        state.repeat_started_at = now
        state.last_repeat_time = now

    def _emit_key_press(self, actions: list[Action], key: str, now: float) -> None:
        if self._apply_special_toggle(key):
            self.state.last_press_time = now
            return
        actions.append(KeyPress(self._format_key_output(key)))
        self.state.last_press_time = now

    def _maybe_repeat(self, actions: list[Action], state: RepeatState, now: float) -> None:
        if state.repeat_key is None or state.repeat_kind is None:
            return
        if state.repeat_key.upper() == "CAPS":
            return
        if now - state.repeat_started_at < self.settings.repeat_initial_delay:
            return
        if now - state.last_repeat_time < self.settings.repeat_interval:
            return
        actions.append(KeyPress(self._format_key_output(state.repeat_key)))
        state.last_repeat_time = now
        self.state.last_press_time = now

    def _update_hand(
        self,
        actions: list[Action],
        side_state: RepeatState,
        cursor_screen: tuple[int, int] | None,
        gesture_label: str | None,
        now: float,
    ) -> str | None:
        hovered = self.hovered_key(cursor_screen)
        side_state.hover_queue.append(hovered)

        gesture = (gesture_label or "idle").lower()
        left_now = gesture == "left_click"
        right_now = gesture == "right_click"

        if left_now:
            key = self._majority_hover(side_state.hover_queue)
            if key is None:
                self._reset_repeat(side_state)
            else:
                if not side_state.active:
                    if (now - self.state.last_press_time) >= self.settings.press_cooldown:
                        self._emit_key_press(actions, key, now)
                        side_state.hover_queue.clear()
                        self._begin_repeat(side_state, "left_click", key, now)
                else:
                    if side_state.repeat_kind != "left_click" or side_state.repeat_key != key:
                        self._begin_repeat(side_state, "left_click", key, now)
                    self._maybe_repeat(actions, side_state, now)
            side_state.active = True

        elif right_now:
            if not side_state.active:
                if (now - self.state.last_press_time) >= self.settings.press_cooldown:
                    actions.append(KeyPress("backspace"))
                    self.state.last_press_time = now
                    side_state.hover_queue.clear()
                    self._begin_repeat(side_state, "right_click", "backspace", now)
            else:
                if side_state.repeat_kind != "right_click" or side_state.repeat_key != "backspace":
                    self._begin_repeat(side_state, "right_click", "backspace", now)
                self._maybe_repeat(actions, side_state, now)
            side_state.active = True

        else:
            side_state.active = False
            self._reset_repeat(side_state)

        return self._majority_hover(side_state.hover_queue) or hovered

    def update(
        self,
        left_cursor_screen: tuple[int, int] | None,
        right_cursor_screen: tuple[int, int] | None,
        left_gesture: str | None,
        right_gesture: str | None,
        now: float,
    ) -> tuple[list[Action], dict]:
        actions: List[Action] = []

        left_hover = self._update_hand(actions, self.state.left, left_cursor_screen, left_gesture, now)
        right_hover = self._update_hand(actions, self.state.right, right_cursor_screen, right_gesture, now)

        highlights = {k for k in [left_hover, right_hover] if k}
        if self.state.caps_on:
            highlights.add("CAPS")

        overlay = {
            "keyboard_visible": True,
            "highlight_labels": highlights,
            "keyboard_layout": self.layout,
            "left_hover": left_hover,
            "right_hover": right_hover,
            "left_pressed": left_hover if (left_gesture or "idle").lower() == "left_click" else None,
            "right_pressed": "BACK" if (right_gesture or "idle").lower() == "right_click" else None,
            "caps_on": self.state.caps_on,
            "keyboard_status": (
                f"Keyboard | CAPS={'ON' if self.state.caps_on else 'OFF'} | "
                f"L={left_hover or '-'}:{(left_gesture or 'idle')} | "
                f"R={right_hover or '-'}:{(right_gesture or 'idle')}"
            ),
        }
        return actions, overlay
