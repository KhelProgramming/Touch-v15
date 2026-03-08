from __future__ import annotations
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QPushButton

from ..controllers.keyboard_controller import KEYBOARD_WINDOW_W, KEYBOARD_WINDOW_H


class KeyboardOverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setFixedSize(KEYBOARD_WINDOW_W, KEYBOARD_WINDOW_H)

        self.left_hover: str | None = None
        self.right_hover: str | None = None
        self.left_pressed: str | None = None
        self.right_pressed: str | None = None
        self.visible_mode = False
        self.locked = False
        self.caps_on = False
        self.keyboard_layout = []

        self.lock_btn = QPushButton("📌", self)
        self.lock_btn.setFixedSize(34, 28)
        self.lock_btn.move(self.width() - 48, 12)
        self.lock_btn.clicked.connect(self.toggle_lock)
        self.lock_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,18);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,32);
            }
        """)

    def toggle_lock(self):
        self.locked = not self.locked
        self.lock_btn.setText("📌" if not self.locked else "🔒")
        self.update()

    def set_locked(self, locked: bool):
        self.locked = locked
        self.lock_btn.setText("🔒" if locked else "📌")
        self.update()

    def set_keyboard_state(
        self,
        visible: bool,
        left_hover: str | None = None,
        right_hover: str | None = None,
        left_pressed: str | None = None,
        right_pressed: str | None = None,
        keyboard_layout=None,
        caps_on: bool = False,
    ):
        self.left_hover = left_hover
        self.right_hover = right_hover
        self.left_pressed = left_pressed
        self.right_pressed = right_pressed
        self.keyboard_layout = list(keyboard_layout or [])
        self.caps_on = caps_on
        self.visible_mode = visible or self.locked

        if self.visible_mode:
            self.show()
        else:
            self.hide()

        self.update()

    def mousePressEvent(self, event):
        event.ignore()

    def mouseMoveEvent(self, event):
        event.ignore()

    def mouseReleaseEvent(self, event):
        event.ignore()

    def _draw_key(self, p: QPainter, key_rect):
        local_rect = QRect(
            int(key_rect.x1 - self.x()),
            int(key_rect.y1 - self.y()),
            int(key_rect.x2 - key_rect.x1),
            int(key_rect.y2 - key_rect.y1),
        )

        key = key_rect.label
        fill = QColor(48, 54, 62, 230)
        outline = QColor(255, 255, 255, 28)

        if key == "CAPS" and self.caps_on:
            fill = QColor(170, 80, 255, 190)
            outline = QColor(220, 180, 255, 100)
        if key == self.left_hover:
            fill = QColor(50, 120, 255, 170)
        if key == self.right_hover:
            fill = QColor(255, 150, 60, 170)
        if key == self.left_pressed:
            fill = QColor(50, 120, 255, 235)
        if key == self.right_pressed:
            fill = QColor(255, 150, 60, 235)
        if key == "CAPS" and self.caps_on and key not in {self.left_pressed, self.right_pressed}:
            outline = QColor(230, 200, 255, 140)

        p.setBrush(QBrush(fill))
        p.setPen(QPen(outline, 1))
        p.drawRoundedRect(local_rect, 14, 14)

        font = QFont()
        font.setBold(True)
        font.setPointSize(16 if len(key) <= 1 else 15)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255))
        p.drawText(local_rect, Qt.AlignCenter, key)

    def paintEvent(self, event):
        if not self.visible_mode:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        p.setBrush(QColor(22, 24, 30, 220))
        p.setPen(QPen(QColor(255, 255, 255, 24), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 22, 22)

        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        p.setFont(title_font)
        p.setPen(QColor(230, 235, 240))
        title = "Keyboard Overlay"
        if self.caps_on:
            title += "  •  CAPS ON"
        p.drawText(QRect(18, 14, 360, 24), Qt.AlignLeft | Qt.AlignVCenter, title)

        for key_rect in self.keyboard_layout:
            self._draw_key(p, key_rect)
