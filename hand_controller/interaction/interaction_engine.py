from __future__ import annotations
import time

from ..config import DEFAULT_LABELS, GatePolicy, KeyboardSettings, ModeSettings, MouseSettings
from ..core.labels import canonicalize_label
from ..controllers.keyboard_controller import KeyboardController
from ..controllers.mode_manager import ModeManager
from ..controllers.mouse_controller import MouseController
from ..ml.gate import accept
from .gesture_memory import GestureMemory


class InteractionEngine:
    def __init__(self, screen_w: int, screen_h: int):
        self.mode_manager = ModeManager(ModeSettings())
        self.mouse = MouseController(screen_w, screen_h, MouseSettings())
        self.keyboard = KeyboardController(screen_w, screen_h, KeyboardSettings())
        self.gate = GatePolicy()
        self.primary_memory = GestureMemory(maxlen=4)
        self.secondary_memory = GestureMemory(maxlen=4)

    def _filter_label(self, label: str | None, p1: float | None = None, margin: float | None = None, allow_hold: bool = False) -> str:
        raw = canonicalize_label(label or DEFAULT_LABELS['idle'])
        if raw == 'redo':
            return DEFAULT_LABELS['idle']
        if raw == 'hold' and not allow_hold:
            return DEFAULT_LABELS['idle']
        if raw == 'toggle':
            return raw
        if p1 is None or margin is None:
            return raw
        return raw if accept(raw, p1, margin, self.gate) else DEFAULT_LABELS['idle']

    def update(self, infer_pkt, now: float | None = None):
        now = now or time.time()
        raw_primary = canonicalize_label(infer_pkt.primary_prediction or DEFAULT_LABELS['idle'])
        raw_secondary = canonicalize_label(infer_pkt.secondary_prediction or DEFAULT_LABELS['idle']) if infer_pkt.secondary_hand_present else DEFAULT_LABELS['idle']
        raw_left = canonicalize_label(getattr(infer_pkt, 'keyboard_left_prediction', None) or DEFAULT_LABELS['idle']) if infer_pkt.keyboard_left_present else DEFAULT_LABELS['idle']
        raw_right = canonicalize_label(getattr(infer_pkt, 'keyboard_right_prediction', None) or DEFAULT_LABELS['idle']) if infer_pkt.keyboard_right_present else DEFAULT_LABELS['idle']

        primary_label = self._filter_label(raw_primary, infer_pkt.p1, infer_pkt.margin, allow_hold=True)
        self.primary_memory.push(primary_label)
        stable_primary = self.primary_memory.majority() or DEFAULT_LABELS['idle']

        self.secondary_memory.push(self._filter_label(raw_secondary))
        stable_secondary = self.secondary_memory.majority() or DEFAULT_LABELS['idle']

        left_label = self._filter_label(raw_left)
        right_label = self._filter_label(raw_right)

        mode = self.mode_manager.update(
            stable_primary,
            stable_secondary,
            infer_pkt.active_hand_present,
            infer_pkt.secondary_hand_present,
            now,
        )

        if mode == 'mouse':
            actions, status = self.mouse.update(infer_pkt.active_cursor_norm, stable_primary, now)
            overlay = {
                'mode': mode,
                'keyboard_visible': False,
                'highlight_labels': set(),
                'keyboard_layout': [],
                'mouse_status': status,
                'keyboard_status': '',
            }
        elif mode == 'keyboard':
            actions, kb_overlay = self.keyboard.update(
                infer_pkt.keyboard_left_cursor_screen,
                infer_pkt.keyboard_right_cursor_screen,
                left_label,
                right_label,
                now,
            )
            overlay = {'mode': mode, 'mouse_status': '', **kb_overlay}
        else:
            actions = []
            overlay = {
                'mode': mode,
                'keyboard_visible': False,
                'highlight_labels': set(),
                'keyboard_layout': [],
                'mouse_status': 'Idle mode',
                'keyboard_status': '',
            }

        overlay.update(
            {
                'prediction': raw_primary,
                'secondary_prediction': raw_secondary if infer_pkt.secondary_hand_present else '-',
                'left_prediction': raw_left if infer_pkt.keyboard_left_present else '-',
                'right_prediction': raw_right if infer_pkt.keyboard_right_present else '-',
                'confidence': infer_pkt.p1,
                'margin': infer_pkt.margin,
                'finger_points': infer_pkt.overlay_points,
                'skeleton_lines': infer_pkt.overlay_lines,
                'selfie_frame': infer_pkt.preview_frame,
            }
        )
        return actions, mode, overlay
