from __future__ import annotations
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PyQt5.QtWidgets import QWidget


class LiveOverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.mode = "Idle"
        self.gesture = "Idle"
        self.fps = 0.0
        self.confidence: float | None = None

        self.overlay_points: list = []
        self.overlay_lines: list = []
        self.active_cursor_screen: tuple[int, int] | None = None
        self.left_cursor_screen: tuple[int, int] | None = None
        self.right_cursor_screen: tuple[int, int] | None = None

        self.show_skeleton = True
        self.show_landmarks = False
        self.show_confidence = False
        self.skeleton_thickness = 2
        self.landmark_radius = 4

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hide()

    def set_screen_geometry(self, x: int, y: int, w: int, h: int):
        self.setGeometry(x, y, w, h)
        self.update()

    def clear_visuals(self):
        self.overlay_points = []
        self.overlay_lines = []
        self.active_cursor_screen = None
        self.left_cursor_screen = None
        self.right_cursor_screen = None
        self.update()

    def update_runtime(
        self,
        mode: str,
        gesture: str,
        fps: float = 0.0,
        confidence: float | None = None,
        overlay_points: list | None = None,
        overlay_lines: list | None = None,
        active_cursor_screen: tuple[int, int] | None = None,
        left_cursor_screen: tuple[int, int] | None = None,
        right_cursor_screen: tuple[int, int] | None = None,
        show_skeleton: bool = True,
        show_landmarks: bool = False,
        show_confidence: bool = False,
        skeleton_thickness: int = 2,
        landmark_radius: int = 4,
    ):
        self.mode = mode
        self.gesture = gesture
        self.fps = fps
        self.confidence = confidence
        self.overlay_points = list(overlay_points or [])
        self.overlay_lines = list(overlay_lines or [])
        self.active_cursor_screen = active_cursor_screen
        self.left_cursor_screen = left_cursor_screen
        self.right_cursor_screen = right_cursor_screen
        self.show_skeleton = show_skeleton
        self.show_landmarks = show_landmarks
        self.show_confidence = show_confidence
        self.skeleton_thickness = skeleton_thickness
        self.landmark_radius = landmark_radius
        self.update()

    def _draw_status_card(self, p: QPainter):
        card_w = 340
        card_h = 114
        card_x = (self.width() - card_w) // 2
        card_y = 24
        rect = QRect(card_x, card_y, card_w, card_h)

        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.setBrush(QBrush(QColor(22, 24, 30, 210)))
        p.drawRoundedRect(rect, 18, 18)

        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        p.setFont(title_font)
        p.setPen(QColor(220, 228, 240))
        p.drawText(QRect(card_x, card_y + 10, card_w, 18), Qt.AlignCenter, "Live Overlay")

        mode_font = QFont()
        mode_font.setPointSize(18)
        mode_font.setBold(True)
        p.setFont(mode_font)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(card_x, card_y + 32, card_w, 24), Qt.AlignCenter, self.mode)

        info_font = QFont()
        info_font.setPointSize(11)
        p.setFont(info_font)
        p.setPen(QColor(208, 215, 226))
        p.drawText(QRect(card_x, card_y + 62, card_w, 18), Qt.AlignCenter, f"Gesture: {self.gesture}")

        info = f"FPS: {self.fps:.1f}"
        if self.show_confidence and self.confidence is not None:
            info += f" | Conf: {self.confidence:.2f}"
        p.setPen(QColor(149, 161, 178))
        p.drawText(QRect(card_x, card_y + 84, card_w, 18), Qt.AlignCenter, info)

    def _draw_cursor(
        self,
        p: QPainter,
        cursor: tuple[int, int] | None,
        color: QColor,
        ring: int = 14,
        dot: int = 6,
        line_width: int = 2,
    ):
        if cursor is None:
            return

        x, y = cursor
        p.setPen(QPen(color, line_width))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(x - ring, y - ring, ring * 2, ring * 2)

        p.setBrush(QBrush(color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(x - dot, y - dot, dot * 2, dot * 2)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        mode_lower = str(self.mode).lower()
        skeleton_width = self.skeleton_thickness + (1 if mode_lower == "keyboard" else 0)

        if self.show_skeleton and self.overlay_lines:
            p.setPen(QPen(QColor(255, 255, 255, 215), skeleton_width))
            for x1, y1, x2, y2 in self.overlay_lines:
                p.drawLine(int(x1), int(y1), int(x2), int(y2))

        if self.show_landmarks and self.overlay_points:
            landmark_r = self.landmark_radius + (1 if mode_lower == "keyboard" else 0)
            p.setPen(QPen(QColor(255, 255, 255, 120), 1))
            p.setBrush(QBrush(QColor(80, 170, 255, 220)))
            for pt in self.overlay_points:
                x = int(pt.get("x", 0))
                y = int(pt.get("y", 0))
                p.drawEllipse(x - landmark_r, y - landmark_r, landmark_r * 2, landmark_r * 2)

        if mode_lower == "mouse":
            self._draw_cursor(
                p,
                self.active_cursor_screen,
                QColor(0, 255, 120, 220),
                ring=14,
                dot=6,
                line_width=2,
            )
        elif mode_lower == "keyboard":
            self._draw_cursor(
                p,
                self.left_cursor_screen,
                QColor(70, 140, 255, 230),
                ring=22,
                dot=8,
                line_width=3,
            )
            self._draw_cursor(
                p,
                self.right_cursor_screen,
                QColor(255, 160, 60, 230),
                ring=22,
                dot=8,
                line_width=3,
            )
        else:
            self._draw_cursor(
                p,
                self.active_cursor_screen,
                QColor(0, 255, 120, 220),
                ring=14,
                dot=6,
                line_width=2,
            )

        self._draw_status_card(p)
        p.end()
