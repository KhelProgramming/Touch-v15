from __future__ import annotations
import argparse
import queue
import threading
import time
from dataclasses import dataclass

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication

from .config import (
    CAMERA_INDEX,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    MLP_LABEL_ENCODER_PATH,
    MLP_MODEL_PATH,
    MLP_SCALER_PATH,
    QUEUE_SIZE,
)
from .ml.mlp_global import GlobalMLP
from .threading.threads.action_exec import exec_loop
from .threading.threads.io_capture import io_capture_loop
from .threading.threads.logic import logic_loop
from .threading.threads.mp_infer import infer_loop
from .ui import UIState, MainWindow, LiveOverlayWindow, CameraPreviewWindow, KeyboardOverlayWindow


class OverlayBridge(QObject):
    """
    Adapter for the existing pipeline.

    Your current exec_loop can keep doing:
        overlay_bus.update_overlay.emit({...})

    and this bridge will route that payload into the new UI windows.
    """
    update_overlay = pyqtSignal(object)

    def __init__(self):
        super().__init__()


@dataclass
class RuntimeSnapshot:
    mode: str = "Idle"
    gesture: str = "Idle"
    fps: float = 0.0
    confidence: float | None = None


class PipelineController:
    def __init__(
        self,
        screen_w: int = 1920,
        screen_h: int = 1080,
        overlay_bus=None,
        ui_state: UIState | None = None,
    ):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.overlay_bus = overlay_bus
        self.ui_state = ui_state or UIState()

        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []

        self.capture_q: queue.Queue = queue.Queue(maxsize=QUEUE_SIZE)
        self.infer_q: queue.Queue = queue.Queue(maxsize=QUEUE_SIZE)
        self.action_q: queue.Queue = queue.Queue(maxsize=QUEUE_SIZE)

        self.metrics = {
            "actions_completed": 0,
            "total_latency_ms": 0.0,
        }

        self.mlp = GlobalMLP(
            str(MLP_SCALER_PATH),
            str(MLP_LABEL_ENCODER_PATH),
            str(MLP_MODEL_PATH),
        )

        self.running = False
        self.snapshot = RuntimeSnapshot()

        # runtime UI-tunable state
        self.runtime_ui_state = self.ui_state

    def start(self):
        if self.running:
            return

        self.stop_event.clear()

        self.threads = [
            threading.Thread(
                target=io_capture_loop,
                name="CameraThread",
                args=(
                    self.stop_event,
                    self.capture_q,
                    CAMERA_INDEX,
                    FRAME_WIDTH,
                    FRAME_HEIGHT,
                ),
                daemon=True,
            ),
            threading.Thread(
                target=infer_loop,
                name="InferThread",
                args=(
                    self.stop_event,
                    self.capture_q,
                    self.infer_q,
                    self.mlp,
                    self.screen_w,
                    self.screen_h,
                ),
                daemon=True,
            ),
            threading.Thread(
                target=logic_loop,
                name="LogicThread",
                args=(
                    self.stop_event,
                    self.infer_q,
                    self.action_q,
                    self.screen_w,
                    self.screen_h,
                ),
                daemon=True,
            ),
            threading.Thread(
                target=exec_loop,
                name="ActionThread",
                args=(
                    self.stop_event,
                    self.action_q,
                    self.overlay_bus,
                    self.metrics,
                ),
                daemon=True,
            ),
        ]

        for t in self.threads:
            t.start()

        self.running = True

    def stop(self):
        if not self.running:
            return

        self.stop_event.set()

        for t in self.threads:
            t.join(timeout=1.0)

        self.running = False

    def set_mouse_sensitivity(self, value: float):
        # value here is already converted from DPI-like scale to air-mouse gain
        self.runtime_ui_state.mouse_sensitivity = value


def _get_screen_size():
    import pyautogui

    pyautogui.FAILSAFE = False
    size = pyautogui.size()
    return int(size.width), int(size.height)


def _compute_default_positions(app: QApplication, overlay_window, camera_window, keyboard_window):
    screen = app.primaryScreen()
    geo = screen.availableGeometry()

    sw = geo.width()
    sh = geo.height()
    sx = geo.x()
    sy = geo.y()

    overlay_x = sx + (sw - overlay_window.width()) // 2
    overlay_y = sy + 20

    camera_x = sx + sw - camera_window.width() - 20
    camera_y = sy + 20

    keyboard_x = sx + (sw - keyboard_window.width()) // 2
    keyboard_y = sy + sh - keyboard_window.height() - 90

    return {
        "screen": (sx, sy),
        "overlay": (overlay_x, overlay_y),
        "camera": (camera_x, camera_y),
        "keyboard": (keyboard_x, keyboard_y),
    }




def _bring_visual_overlay_to_front(overlay_window, keyboard_window, mode: str, ui_state: UIState):
    mode_lower = str(mode).lower()
    try:
        if mode_lower == "keyboard" and ui_state.show_keyboard_overlay:
            if keyboard_window.isVisible():
                keyboard_window.raise_()
            if ui_state.show_overlay and overlay_window.isVisible():
                overlay_window.raise_()
        elif ui_state.show_overlay and overlay_window.isVisible():
            overlay_window.raise_()
    except Exception:
        pass
def _dpi_to_air_sensitivity(dpi: int) -> float:
    """
    Convert mouse-like DPI into air-mouse gain.
    800 DPI is the neutral baseline.
    """
    return dpi / 1600.0


def run_headless():
    screen_w, screen_h = _get_screen_size()
    controller = PipelineController(screen_w, screen_h, overlay_bus=None)
    controller.start()

    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        controller.stop()


def run_gui():
    app = QApplication([])

    screen_w, screen_h = _get_screen_size()
    ui_state = UIState()
    overlay_bus = OverlayBridge()

    controller = PipelineController(
        screen_w=screen_w,
        screen_h=screen_h,
        overlay_bus=overlay_bus,
        ui_state=ui_state,
    )

    # -----------------------------
    # Create windows
    # -----------------------------
    main_window = MainWindow()
    overlay_window = LiveOverlayWindow()
    camera_window = CameraPreviewWindow()
    keyboard_window = KeyboardOverlayWindow()

    positions = _compute_default_positions(app, overlay_window, camera_window, keyboard_window)

    ui_state.overlay_x, ui_state.overlay_y = positions["overlay"]
    ui_state.camera_x, ui_state.camera_y = positions["camera"]
    ui_state.keyboard_x, ui_state.keyboard_y = positions["keyboard"]

    overlay_window.set_screen_geometry(positions["screen"][0], positions["screen"][1], screen_w, screen_h)
    camera_window.move(ui_state.camera_x, ui_state.camera_y)
    keyboard_window.move(ui_state.keyboard_x, ui_state.keyboard_y)

    main_window.show()
    overlay_window.hide()
    camera_window.hide()
    keyboard_window.hide()

    # -----------------------------
    # Overlay payload adapter
    # -----------------------------
    def _apply_overlay_state(payload):
        if not isinstance(payload, dict):
            return

        mode = str(
            payload.get("mode")
            or payload.get("mode_text")
            or payload.get("status_mode")
            or "Idle"
        )

        gesture = str(
            payload.get("gesture")
            or payload.get("gesture_label")
            or payload.get("label")
            or payload.get("status_gesture")
            or "Idle"
        )

        fps = float(payload.get("fps", 0.0) or 0.0)

        confidence = payload.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except Exception:
                confidence = None

        controller.snapshot.mode = mode
        controller.snapshot.gesture = gesture
        controller.snapshot.fps = fps
        controller.snapshot.confidence = confidence

        # Update top-level windows
        overlay_window.update_runtime(
            mode=mode,
            gesture=gesture,
            fps=fps,
            confidence=confidence if ui_state.show_confidence else None,
            overlay_points=payload.get("overlay_points") or payload.get("finger_points") or [],
            overlay_lines=payload.get("overlay_lines") or payload.get("skeleton_lines") or [],
            active_cursor_screen=payload.get("active_cursor_screen"),
            left_cursor_screen=payload.get("keyboard_left_cursor_screen"),
            right_cursor_screen=payload.get("keyboard_right_cursor_screen"),
            show_skeleton=ui_state.show_skeleton,
            show_landmarks=ui_state.show_landmarks,
            show_confidence=ui_state.show_confidence,
            skeleton_thickness=ui_state.skeleton_thickness,
            landmark_radius=ui_state.landmark_radius,
        )

        main_window.update_status(
            running=controller.running,
            mode=mode,
            fps=fps,
        )

        # Keyboard overlay state
        left_hover = payload.get("left_hover")
        right_hover = payload.get("right_hover")
        left_pressed = payload.get("left_pressed")
        right_pressed = payload.get("right_pressed")

        keyboard_window.set_locked(ui_state.keyboard_locked)
        keyboard_window.set_keyboard_state(
            visible=(mode.lower() == "keyboard" and ui_state.show_keyboard_overlay),
            left_hover=left_hover,
            right_hover=right_hover,
            left_pressed=left_pressed,
            right_pressed=right_pressed,
            keyboard_layout=payload.get("keyboard_layout") or [],
            caps_on=bool(payload.get("caps_on", False)),
        )

        # Keep UI state synchronized if user toggled lock button directly on keyboard
        try:
            ui_state.keyboard_locked = bool(keyboard_window.locked)
        except Exception:
            pass

        # Optional camera preview frame
        frame_bgr = payload.get("frame_bgr") or payload.get("preview_frame")
        overlay_lines = payload.get("overlay_lines")
        overlay_points = payload.get("overlay_points")

        if ui_state.show_camera and frame_bgr is not None:
            camera_window.update_frame(frame_bgr)

        _bring_visual_overlay_to_front(overlay_window, keyboard_window, mode, ui_state)

    overlay_bus.update_overlay.connect(_apply_overlay_state)

    # -----------------------------
    # Settings handlers
    # -----------------------------
    settings = main_window.settings

    def _start_system():
        controller.start()
        if ui_state.show_overlay and not ui_state.overlay_minimized:
            overlay_window.show()
        if ui_state.show_camera and not ui_state.camera_minimized:
            camera_window.show()
        _bring_visual_overlay_to_front(overlay_window, keyboard_window, controller.snapshot.mode, ui_state)
        main_window.update_status(
            running=True,
            mode=controller.snapshot.mode,
            fps=controller.snapshot.fps,
        )

    def _stop_system():
        controller.stop()
        overlay_window.hide()
        overlay_window.clear_visuals()
        camera_window.hide()
        camera_window.clear_frame()
        if not ui_state.keyboard_locked:
            keyboard_window.hide()
        main_window.update_status(
            running=False,
            mode=controller.snapshot.mode,
            fps=controller.snapshot.fps,
        )

    def _handle_show_overlay(checked: bool):
        ui_state.show_overlay = checked
        if controller.running and checked and not ui_state.overlay_minimized:
            overlay_window.show()
        else:
            overlay_window.hide()

    def _handle_show_camera(checked: bool):
        ui_state.show_camera = checked
        if controller.running and checked and not ui_state.camera_minimized:
            camera_window.show()
        else:
            camera_window.hide()
        _bring_visual_overlay_to_front(overlay_window, keyboard_window, controller.snapshot.mode, ui_state)

    def _handle_show_skeleton(checked: bool):
        ui_state.show_skeleton = checked

    def _handle_show_landmarks(checked: bool):
        ui_state.show_landmarks = checked

    def _handle_skeleton_thickness(value: int):
        ui_state.skeleton_thickness = value

    def _handle_mouse_dpi(dpi: int):
        ui_state.mouse_dpi = dpi
        controller.set_mouse_sensitivity(_dpi_to_air_sensitivity(dpi))

    def _reset_window_positions():
        positions = _compute_default_positions(app, overlay_window, camera_window, keyboard_window)

        ui_state.overlay_x, ui_state.overlay_y = positions["overlay"]
        ui_state.camera_x, ui_state.camera_y = positions["camera"]
        ui_state.keyboard_x, ui_state.keyboard_y = positions["keyboard"]

        overlay_window.set_screen_geometry(positions["screen"][0], positions["screen"][1], screen_w, screen_h)
        camera_window.move(ui_state.camera_x, ui_state.camera_y)
        keyboard_window.move(ui_state.keyboard_x, ui_state.keyboard_y)

    settings.start_requested.connect(_start_system)
    settings.stop_requested.connect(_stop_system)
    settings.show_overlay_changed.connect(_handle_show_overlay)
    settings.show_camera_changed.connect(_handle_show_camera)
    settings.show_skeleton_changed.connect(_handle_show_skeleton)
    settings.show_landmarks_changed.connect(_handle_show_landmarks)
    settings.skeleton_thickness_changed.connect(_handle_skeleton_thickness)
    settings.mouse_dpi_changed.connect(_handle_mouse_dpi)
    settings.reset_positions_requested.connect(_reset_window_positions)

    # apply initial DPI-like default immediately
    controller.set_mouse_sensitivity(_dpi_to_air_sensitivity(ui_state.mouse_dpi))

    # -----------------------------
    # UI refresh timer
    # keeps main window labels live even if no new overlay payload arrives
    # -----------------------------
    timer = QTimer()
    timer.setInterval(200)

    def _refresh_ui():
        main_window.update_status(
            running=controller.running,
            mode=controller.snapshot.mode,
            fps=controller.snapshot.fps,
        )

        if controller.running:
            if ui_state.show_overlay and not overlay_window.isVisible() and not ui_state.overlay_minimized:
                overlay_window.show()
            if (not ui_state.show_overlay) and overlay_window.isVisible():
                overlay_window.hide()

            if ui_state.show_camera and not camera_window.isVisible() and not ui_state.camera_minimized:
                camera_window.show()
            if (not ui_state.show_camera) and camera_window.isVisible():
                camera_window.hide()

            _bring_visual_overlay_to_front(overlay_window, keyboard_window, controller.snapshot.mode, ui_state)
        else:
            if overlay_window.isVisible():
                overlay_window.hide()
            if camera_window.isVisible():
                camera_window.hide()
            if keyboard_window.isVisible() and not ui_state.keyboard_locked:
                keyboard_window.hide()

        # keep keyboard lock state synced in case user toggled the button directly
        try:
            ui_state.keyboard_locked = bool(keyboard_window.locked)
        except Exception:
            pass

    timer.timeout.connect(_refresh_ui)
    timer.start()   

    try:
        app.exec_()
    finally:
        timer.stop()
        controller.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if args.headless:
        run_headless()
    else:
        run_gui()


if __name__ == "__main__":
    main()