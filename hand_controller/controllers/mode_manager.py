from __future__ import annotations
from dataclasses import dataclass

from ..config import ModeSettings


@dataclass(slots=True)
class ModeState:
    mode: str = "idle"
    toggle_start: float | None = None
    both_idle_start: float | None = None
    no_hands_start: float | None = None
    last_switch_time: float = -1e9


class ModeManager:
    def __init__(self, settings: ModeSettings | None = None, state: ModeState | None = None):
        self.settings = settings or ModeSettings()
        self.state = state or ModeState()

    @property
    def mode(self) -> str:
        return self.state.mode

    def update(
        self,
        primary_label: str | None,
        secondary_label: str | None,
        primary_present: bool,
        secondary_present: bool,
        now: float,
    ) -> str:
        primary = (primary_label or "idle").lower()
        secondary = (secondary_label or "").lower()

        toggle_detected = primary_present and primary == "toggle"
        if toggle_detected:
            if self.state.toggle_start is None:
                self.state.toggle_start = now
            if (
                now - self.state.toggle_start >= self.settings.toggle_hold_seconds
                and now - self.state.last_switch_time >= self.settings.toggle_cooldown_seconds
            ):
                if self.state.mode == "mouse":
                    self.state.mode = "idle"
                else:
                    self.state.mode = "mouse"
                self.state.last_switch_time = now
                self.state.toggle_start = None
                self.state.both_idle_start = None
                self.state.no_hands_start = None
                return self.state.mode
        else:
            self.state.toggle_start = None

        if self.state.mode != "keyboard":
            both_idle = (
                primary_present
                and secondary_present
                and primary == "idle"
                and secondary == "idle"
            )
            if both_idle:
                if self.state.both_idle_start is None:
                    self.state.both_idle_start = now
                if (
                    now - self.state.both_idle_start >= self.settings.keyboard_idle_hold_seconds
                    and now - self.state.last_switch_time >= self.settings.toggle_cooldown_seconds
                ):
                    self.state.mode = "keyboard"
                    self.state.last_switch_time = now
                    self.state.both_idle_start = None
                    self.state.toggle_start = None
                    self.state.no_hands_start = None
            else:
                self.state.both_idle_start = None
        else:
            self.state.both_idle_start = None
            no_hands = (not primary_present) and (not secondary_present)
            if no_hands:
                if self.state.no_hands_start is None:
                    self.state.no_hands_start = now
                if (
                    now - self.state.no_hands_start >= self.settings.keyboard_exit_no_hands_seconds
                    and now - self.state.last_switch_time >= self.settings.toggle_cooldown_seconds
                ):
                    self.state.mode = "idle"
                    self.state.last_switch_time = now
                    self.state.no_hands_start = None
                    self.state.toggle_start = None
            else:
                self.state.no_hands_start = None

        return self.state.mode
