from __future__ import annotations
from dataclasses import dataclass


@dataclass
class UIState:
    show_overlay: bool = True
    show_camera: bool = True
    show_keyboard_overlay: bool = True

    show_skeleton: bool = True
    show_landmarks: bool = False
    show_fps: bool = True
    show_confidence: bool = False

    skeleton_thickness: int = 2
    landmark_radius: int = 3

    # DPI-like air mouse setting
    # 800 is a good balanced default
    mouse_dpi: int = 800

    overlay_minimized: bool = False
    camera_minimized: bool = False
    keyboard_locked: bool = False

    overlay_x: int = 0
    overlay_y: int = 0

    camera_x: int = 0
    camera_y: int = 0

    keyboard_x: int = 0
    keyboard_y: int = 0