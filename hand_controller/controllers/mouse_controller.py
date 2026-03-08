from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import List
import math

from ..config import MouseSettings
from .actions import Action, Click, DoubleClick, Hotkey, MouseDown, MouseUp, MoveRelative, KeyDown, KeyUp, KeyPress


@dataclass(slots=True)
class MouseState:
    prev_x: float | None = None
    prev_y: float | None = None
    filtered_x: float | None = None
    filtered_y: float | None = None
    last_seen: float = 0.0
    deltas: deque = field(default_factory=lambda: deque(maxlen=2))

    drag_active: bool = False
    left_active: bool = False
    right_active: bool = False
    undo_active: bool = False
    hold_active: bool = False
    alt_held: bool = False

    left_press_started: float | None = None
    last_click_time: float = 0.0

    last_right_click: float = 0.0
    last_shortcut: float = 0.0
    hold_started_at: float | None = None
    last_alt_tab_time: float = 0.0

    smooth_dx: float = 0.0
    smooth_dy: float = 0.0
    motion_awake: bool = False


class MouseController:
    def __init__(self, screen_w: int, screen_h: int, settings: MouseSettings | None = None):
        self.settings = settings or MouseSettings()
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.state = MouseState(deltas=deque(maxlen=self.settings.smoothing_window))

    def _reset_motion(self) -> None:
        self.state.prev_x = None
        self.state.prev_y = None
        self.state.filtered_x = None
        self.state.filtered_y = None
        self.state.deltas.clear()
        self.state.smooth_dx = 0.0
        self.state.smooth_dy = 0.0
        self.state.motion_awake = False

    def _release_alt_if_needed(self, actions: list[Action]) -> None:
        if self.state.alt_held:
            actions.append(KeyUp("alt"))
            self.state.alt_held = False
        self.state.hold_started_at = None
        self.state.last_alt_tab_time = 0.0

    def _shape_delta(self, dx: float, dy: float) -> tuple[float, float]:
        magnitude = math.hypot(dx, dy)
        if magnitude <= 1e-6:
            return 0.0, 0.0

        if magnitude > self.settings.spike_clamp_px:
            scale = self.settings.spike_clamp_px / magnitude
            dx *= scale
            dy *= scale
            magnitude = self.settings.spike_clamp_px

        shaped_mag = magnitude ** self.settings.gain_exponent
        if magnitude >= self.settings.accel_start_px:
            shaped_mag *= self.settings.fast_gain

        scale = shaped_mag / magnitude
        return dx * scale, dy * scale

    def _filter_anchor(self, x: float, y: float) -> tuple[float, float]:
        alpha = self.settings.anchor_alpha
        if self.state.filtered_x is None or self.state.filtered_y is None or alpha >= 0.999:
            self.state.filtered_x = x
            self.state.filtered_y = y
        else:
            self.state.filtered_x = alpha * x + (1.0 - alpha) * self.state.filtered_x
            self.state.filtered_y = alpha * y + (1.0 - alpha) * self.state.filtered_y
        return self.state.filtered_x, self.state.filtered_y

    def _apply_motion_gate(self, dx: float, dy: float) -> tuple[float, float]:
        mag = math.hypot(dx, dy)

        if self.state.motion_awake:
            if mag <= self.settings.sleep_threshold_px:
                self.state.motion_awake = False
                self.state.smooth_dx = 0.0
                self.state.smooth_dy = 0.0
                self.state.deltas.clear()
                return 0.0, 0.0
        else:
            if mag < self.settings.wake_threshold_px:
                return 0.0, 0.0
            self.state.motion_awake = True

        if abs(dx) < self.settings.micro_jitter_px:
            dx = 0.0
        if abs(dy) < self.settings.micro_jitter_px:
            dy = 0.0

        return dx, dy

    def update(
        self,
        cursor_norm: tuple[float, float] | None,
        gesture_label: str | None,
        now: float,
    ) -> tuple[list[Action], str]:
        actions: List[Action] = []
        gesture = (gesture_label or "idle").lower()

        if cursor_norm is None:
            if self.state.drag_active:
                actions.append(MouseUp())
            self._release_alt_if_needed(actions)
            self.state.drag_active = False
            self.state.left_active = False
            self.state.right_active = False
            self.state.undo_active = False
            self.state.hold_active = False
            self.state.left_press_started = None
            self._reset_motion()
            return actions, "Mouse | no hand"

        x, y = cursor_norm

        if self.state.last_seen > 0.0 and (now - self.state.last_seen) > self.settings.move_timeout:
            self._reset_motion()

        filt_x, filt_y = self._filter_anchor(x, y)
        self.state.last_seen = now

        if self.state.prev_x is not None and self.state.prev_y is not None:
            raw_dx = (filt_x - self.state.prev_x) * self.screen_w * self.settings.sensitivity
            raw_dy = (filt_y - self.state.prev_y) * self.screen_h * self.settings.sensitivity

            jump_mag = math.hypot(raw_dx, raw_dy)
            if jump_mag >= self.settings.reanchor_distance_px:
                self._reset_motion()
                self.state.prev_x = filt_x
                self.state.prev_y = filt_y
            else:
                gated_dx, gated_dy = self._apply_motion_gate(raw_dx, raw_dy)
                shaped_dx, shaped_dy = self._shape_delta(gated_dx, gated_dy)

                alpha = self.settings.ema_alpha if self.state.motion_awake else 1.0
                self.state.smooth_dx = alpha * shaped_dx + (1.0 - alpha) * self.state.smooth_dx
                self.state.smooth_dy = alpha * shaped_dy + (1.0 - alpha) * self.state.smooth_dy

                self.state.deltas.append((self.state.smooth_dx, self.state.smooth_dy))
                avg_dx = sum(d[0] for d in self.state.deltas) / len(self.state.deltas)
                avg_dy = sum(d[1] for d in self.state.deltas) / len(self.state.deltas)

                avg_dx = max(-self.settings.max_step_px, min(self.settings.max_step_px, avg_dx))
                avg_dy = max(-self.settings.max_step_px, min(self.settings.max_step_px, avg_dy))

                move_dx = int(round(avg_dx))
                move_dy = int(round(avg_dy))

                if move_dx != 0 or move_dy != 0:
                    actions.append(MoveRelative(move_dx, move_dy))

        self.state.prev_x = filt_x
        self.state.prev_y = filt_y

        left_now = gesture == "left_click"
        if left_now and not self.state.left_active:
            self.state.left_press_started = now

        if (
            left_now
            and self.state.left_press_started is not None
            and not self.state.drag_active
            and (now - self.state.left_press_started) >= self.settings.left_hold_drag_seconds
        ):
            actions.append(MouseDown())
            self.state.drag_active = True

        if not left_now and self.state.left_active:
            press_duration = 0.0
            if self.state.left_press_started is not None:
                press_duration = now - self.state.left_press_started

            if self.state.drag_active:
                actions.append(MouseUp())
                self.state.drag_active = False
            else:
                if press_duration < self.settings.left_hold_drag_seconds:
                    if (now - self.state.last_click_time) < self.settings.double_click_interval:
                        actions.append(DoubleClick())
                        self.state.last_click_time = 0.0
                    else:
                        actions.append(Click("left"))
                        self.state.last_click_time = now

            self.state.left_press_started = None

        self.state.left_active = left_now

        right_now = gesture == "right_click"
        if (
            right_now
            and not self.state.right_active
            and (now - self.state.last_right_click) >= self.settings.click_cooldown
            and not self.state.drag_active
        ):
            actions.append(Click("right"))
            self.state.last_right_click = now
        self.state.right_active = right_now

        undo_now = gesture == "undo"
        if (
            undo_now
            and not self.state.undo_active
            and (now - self.state.last_shortcut) >= self.settings.shortcut_cooldown
        ):
            actions.append(Hotkey(("ctrl", "z")))
            self.state.last_shortcut = now
        self.state.undo_active = undo_now

        hold_now = gesture == "hold"
        if hold_now:
            if self.state.hold_started_at is None:
                self.state.hold_started_at = now
            if not self.state.alt_held and (now - self.state.hold_started_at) >= 0.30:
                actions.append(KeyDown("alt"))
                actions.append(KeyPress("tab"))
                self.state.alt_held = True
                self.state.last_alt_tab_time = now
            elif self.state.alt_held and (now - self.state.last_alt_tab_time) >= 1.0:
                actions.append(KeyPress("tab"))
                self.state.last_alt_tab_time = now
        else:
            self._release_alt_if_needed(actions)
        self.state.hold_active = hold_now

        status = f"Mouse | {gesture}"
        if self.state.drag_active:
            status += " | dragging"
        if self.state.motion_awake:
            status += " | moving"
        if self.state.alt_held:
            status += " | alt-tab"

        return actions, status
