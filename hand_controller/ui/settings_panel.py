from __future__ import annotations
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSlider, QGroupBox
)


class SettingsPanel(QWidget):
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    reset_positions_requested = pyqtSignal()

    show_overlay_changed = pyqtSignal(bool)
    show_camera_changed = pyqtSignal(bool)
    show_skeleton_changed = pyqtSignal(bool)
    show_landmarks_changed = pyqtSignal(bool)

    skeleton_thickness_changed = pyqtSignal(int)
    mouse_dpi_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # -----------------------------
        # System group
        # -----------------------------
        system_group = QGroupBox("System")
        system_layout = QVBoxLayout(system_group)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.reset_btn = QPushButton("Reset Window Positions")

        self.start_btn.clicked.connect(self.start_requested.emit)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        self.reset_btn.clicked.connect(self.reset_positions_requested.emit)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.reset_btn)

        system_layout.addLayout(btn_row)

        # -----------------------------
        # Display group
        # -----------------------------
        display_group = QGroupBox("Display")
        display_layout = QVBoxLayout(display_group)

        self.overlay_cb = QCheckBox("Show Live Overlay")
        self.overlay_cb.setChecked(True)
        self.overlay_cb.toggled.connect(self.show_overlay_changed.emit)

        self.camera_cb = QCheckBox("Show Camera Preview")
        self.camera_cb.setChecked(True)
        self.camera_cb.toggled.connect(self.show_camera_changed.emit)

        self.skeleton_cb = QCheckBox("Show Hand Skeleton")
        self.skeleton_cb.setChecked(True)
        self.skeleton_cb.toggled.connect(self.show_skeleton_changed.emit)

        self.landmarks_cb = QCheckBox("Show Landmarks")
        self.landmarks_cb.setChecked(False)
        self.landmarks_cb.toggled.connect(self.show_landmarks_changed.emit)

        display_layout.addWidget(self.overlay_cb)
        display_layout.addWidget(self.camera_cb)
        display_layout.addWidget(self.skeleton_cb)
        display_layout.addWidget(self.landmarks_cb)

        # -----------------------------
        # Mouse group
        # -----------------------------
        mouse_group = QGroupBox("Mouse")
        mouse_layout = QVBoxLayout(mouse_group)

        self.dpi_value = QLabel("800 DPI")
        self.dpi_slider = QSlider(Qt.Horizontal)

        # 400 to 3200 DPI-like range, step 100
        self.dpi_slider.setRange(4, 32)
        self.dpi_slider.setValue(8)
        self.dpi_slider.valueChanged.connect(self._emit_dpi)

        mouse_layout.addWidget(QLabel("Mouse DPI"))
        mouse_layout.addWidget(self.dpi_slider)
        mouse_layout.addWidget(self.dpi_value)

        # -----------------------------
        # Visual group
        # -----------------------------
        visual_group = QGroupBox("Visual")
        visual_layout = QVBoxLayout(visual_group)

        self.thickness_value = QLabel("2")
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 8)
        self.thickness_slider.setValue(2)
        self.thickness_slider.valueChanged.connect(self._emit_thickness)

        visual_layout.addWidget(QLabel("Skeleton Thickness"))
        visual_layout.addWidget(self.thickness_slider)
        visual_layout.addWidget(self.thickness_value)

        root.addWidget(system_group)
        root.addWidget(display_group)
        root.addWidget(mouse_group)
        root.addWidget(visual_group)
        root.addStretch(1)

    def _emit_thickness(self, value: int):
        self.thickness_value.setText(str(value))
        self.skeleton_thickness_changed.emit(value)

    def _emit_dpi(self, value: int):
        dpi = value * 100
        self.dpi_value.setText(f"{dpi} DPI")
        self.mouse_dpi_changed.emit(dpi)