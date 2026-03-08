from __future__ import annotations
import cv2

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame


class DragMixin:
    def __init__(self):
        self._drag_pos: QPoint | None = None

    def _start_drag(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos()

    def _move_drag(self, event):
        if self._drag_pos is not None:
            delta = event.globalPos() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPos()

    def _end_drag(self, event):
        self._drag_pos = None


class TitleBar(QFrame):
    def __init__(self, title: str, on_minimize, on_close, parent=None):
        super().__init__(parent)
        self._start_drag_cb = None
        self._move_drag_cb = None
        self._end_drag_cb = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        self.title = QLabel(title)

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(28, 22)
        self.min_btn.clicked.connect(on_minimize)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(28, 22)
        self.close_btn.clicked.connect(on_close)

        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    def bind_drag(self, start_cb, move_cb, end_cb):
        self._start_drag_cb = start_cb
        self._move_drag_cb = move_cb
        self._end_drag_cb = end_cb

    def mousePressEvent(self, event):
        if self._start_drag_cb:
            self._start_drag_cb(event)

    def mouseMoveEvent(self, event):
        if self._move_drag_cb:
            self._move_drag_cb(event)

    def mouseReleaseEvent(self, event):
        if self._end_drag_cb:
            self._end_drag_cb(event)


class CameraPreviewWindow(QWidget, DragMixin):
    def __init__(self):
        QWidget.__init__(self)
        DragMixin.__init__(self)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(420, 360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("Card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 10)
        card_layout.setSpacing(10)

        self.title_bar = TitleBar("Camera Preview", self.toggle_minimize, self.hide)
        self.title_bar.bind_drag(self._start_drag, self._move_drag, self._end_drag)

        self.image_label = QLabel("No Camera Frame")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(400, 300)
        self.image_label.setStyleSheet("background: rgba(255,255,255,10); border-radius: 12px; color: white;")

        card_layout.addWidget(self.title_bar)
        card_layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        outer.addWidget(self.card)

        self._minimized = False
        self._full_height = self.height()

        self.setStyleSheet("""
            QFrame#Card {
                background: rgba(22, 24, 30, 235);
                border: 1px solid rgba(255,255,255,24);
                border-radius: 18px;
            }
            QLabel {
                color: white;
                font-size: 13px;
            }
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

    def toggle_minimize(self):
        self._minimized = not self._minimized
        self.image_label.setVisible(not self._minimized)
        self.setFixedHeight(44 if self._minimized else self._full_height)

    def clear_frame(self):
        self.image_label.clear()
        self.image_label.setText("No Camera Frame")

    def update_frame(self, frame_bgr):
        if frame_bgr is None:
            return

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(image).scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(pix)
