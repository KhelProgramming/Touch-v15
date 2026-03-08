from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"

MLP_SCALER_PATH = ARTIFACTS_DIR / "validator_scaler.joblib"
MLP_LABEL_ENCODER_PATH = ARTIFACTS_DIR / "validator_label_encoder.joblib"
MLP_MODEL_PATH = ARTIFACTS_DIR / "validator_MLP.joblib"

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
QUEUE_SIZE = 2

DEFAULT_LABELS = {
    "idle": "idle",
    "left_click": "left_click",
    "right_click": "right_click",
    "hold": "hold",
    "toggle": "toggle",
    "undo": "undo",
    "redo": "redo",
}


@dataclass(slots=True)
class MouseSettings:
    sensitivity: float = 0.95
    smoothing_window: int = 2
    ema_alpha: float = 0.58
    anchor_alpha: float = 1.0
    sleep_threshold_px: float = 1.25
    wake_threshold_px: float = 3.20
    micro_jitter_px: float = 0.90
    gain_exponent: float = 1.02
    accel_start_px: float = 5.0
    fast_gain: float = 1.10
    spike_clamp_px: float = 48.0
    reanchor_distance_px: float = 140.0
    max_step_px: float = 30.0
    move_timeout: float = 0.35
    click_cooldown: float = 0.24
    double_click_interval: float = 0.42
    drag_grace: float = 0.30
    left_hold_drag_seconds: float = 0.40
    shortcut_cooldown: float = 0.60


@dataclass(slots=True)
class KeyboardSettings:
    hover_window: int = 7
    press_cooldown: float = 0.38
    repeat_initial_delay: float = 0.42
    repeat_interval: float = 0.075
    height_ratio: float = 0.34
    side_margin: int = 110


@dataclass(slots=True)
class ModeSettings:
    toggle_hold_seconds: float = 1.5
    toggle_cooldown_seconds: float = 1.0
    keyboard_idle_hold_seconds: float = 2.0
    keyboard_exit_no_hands_seconds: float = 2.0
    flicker_grace_seconds: float = 0.25


@dataclass(slots=True)
class GatePolicy:
    min_p1: float = 0.42
    min_margin: float = 0.05


@dataclass(slots=True)
class SelectorSettings:
    switch_margin: float = 0.18
    lost_grace_seconds: float = 0.30
    centroid_switch_px: float = 85.0
