from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FramePacket:
    t_capture: float
    frame_bgr: Any


@dataclass(slots=True)
class InferPacket:
    t_capture: float
    frame_w: int
    frame_h: int

    active_hand_present: bool
    active_hand_label: str | None
    active_cursor_norm: tuple[float, float] | None
    active_cursor_screen: tuple[int, int] | None
    secondary_hand_present: bool

    keyboard_left_present: bool = False
    keyboard_left_label: str | None = None
    keyboard_left_cursor_screen: tuple[int, int] | None = None
    keyboard_left_prediction: str | None = None
    keyboard_right_present: bool = False
    keyboard_right_label: str | None = None
    keyboard_right_cursor_screen: tuple[int, int] | None = None
    keyboard_right_prediction: str | None = None

    primary_prediction: str = "idle"
    secondary_prediction: str | None = None
    label: str = "idle"
    p1: float = 1.0
    margin: float = 1.0
    overlay_points: list = field(default_factory=list)
    overlay_lines: list = field(default_factory=list)
    preview_frame: Any | None = None


@dataclass(slots=True)
class ActionPacket:
    t_capture: float
    mode: str
    actions: list
    overlay_state: dict
