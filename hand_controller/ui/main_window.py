from __future__ import annotations
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel

from .settings_panel import SettingsPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Gesture Controller")
        self.resize(420, 520)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.status_label = QLabel("Status: Stopped")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.mode_label = QLabel("Mode: Idle")
        self.fps_label = QLabel("FPS: 0.0")

        self.settings = SettingsPanel()

        layout.addWidget(self.status_label)
        layout.addWidget(self.mode_label)
        layout.addWidget(self.fps_label)
        layout.addWidget(self.settings)

    def update_status(self, running: bool, mode: str, fps: float):
        self.status_label.setText(f"Status: {'Running' if running else 'Stopped'}")
        self.mode_label.setText(f"Mode: {mode}")
        self.fps_label.setText(f"FPS: {fps:.1f}")