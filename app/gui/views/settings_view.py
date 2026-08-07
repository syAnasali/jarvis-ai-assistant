"""Expanded 5-tab SettingsView workspace managing application configuration and UX preferences."""

from typing import Any, Optional
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt


class SettingsView(QWidget):
    """Expanded 5-tab SettingsView managing Appearance, Behavior, Voice/Vision, Plugins/Privacy, and Performance."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        lbl_title = QLabel("Application Settings & UX Configuration")
        lbl_title.setObjectName("headerTitle")
        layout.addWidget(lbl_title)

        # Tab Widget
        self.tabs = QTabWidget(self)

        # Tab 1: Appearance & Themes
        t1 = QWidget()
        l1 = QFormLayout(t1)
        l1.setContentsMargins(12, 12, 12, 12)

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["Dark (Indigo HSL)", "Light (Clean Slate)"])
        l1.addRow("UI Color Theme:", self.cmb_theme)

        self.cmb_accent = QComboBox()
        self.cmb_accent.addItems(["Indigo (#6366f1)", "Emerald (#10b981)", "Sky Blue (#38bdf8)", "Rose (#f43f5e)"])
        l1.addRow("Accent Color:", self.cmb_accent)

        self.spin_font = QSpinBox()
        self.spin_font.setRange(8, 20)
        self.spin_font.setValue(11)
        l1.addRow("Font Scale (pt):", self.spin_font)

        self.chk_high_dpi = QCheckBox("Enable High-DPI Display Scaling")
        self.chk_high_dpi.setChecked(True)
        l1.addRow("Display Scaling:", self.chk_high_dpi)

        self.tabs.addTab(t1, "🎨 Appearance")

        # Tab 2: Behavior & Startup
        t2 = QWidget()
        l2 = QFormLayout(t2)
        l2.setContentsMargins(12, 12, 12, 12)

        self.chk_restore = QCheckBox("Restore Last Active Session & Drafts on Startup")
        self.chk_restore.setChecked(True)
        l2.addRow("Session Restore:", self.chk_restore)

        self.chk_tray = QCheckBox("Minimize to System Tray on Close")
        self.chk_tray.setChecked(False)
        l2.addRow("System Tray:", self.chk_tray)

        self.chk_notify = QCheckBox("Enable Native Toast Notifications")
        self.chk_notify.setChecked(True)
        l2.addRow("Notifications:", self.chk_notify)

        self.tabs.addTab(t2, "⚙️ Behavior")

        # Tab 3: Voice & Vision
        t3 = QWidget()
        l3 = QFormLayout(t3)
        l3.setContentsMargins(12, 12, 12, 12)

        self.cmb_mic = QComboBox()
        self.cmb_mic.addItems(["Default System Microphone", "Realtek High Definition Audio", "Virtual Audio Cable"])
        l3.addRow("Input Device:", self.cmb_mic)

        self.spin_wake = QSpinBox()
        self.spin_wake.setRange(1, 100)
        self.spin_wake.setValue(75)
        l3.addRow("Wake-Word Sensitivity (%):", self.spin_wake)

        self.cmb_vision = QComboBox()
        self.cmb_vision.addItems(["High Quality (1080p)", "Medium Quality (720p)", "Fast (480p)"])
        l3.addRow("Screen Capture Resolution:", self.cmb_vision)

        self.tabs.addTab(t3, "🎙️ Voice & Vision")

        # Tab 4: Plugins & Privacy
        t4 = QWidget()
        l4 = QFormLayout(t4)
        l4.setContentsMargins(12, 12, 12, 12)

        self.chk_sandbox = QCheckBox("Strict Permission Sandboxing for Plugins")
        self.chk_sandbox.setChecked(True)
        l4.addRow("Sandboxing:", self.chk_sandbox)

        self.spin_telemetry = QSpinBox()
        self.spin_telemetry.setRange(1, 90)
        self.spin_telemetry.setValue(30)
        l4.addRow("Telemetry Log Retention (Days):", self.spin_telemetry)

        self.tabs.addTab(t4, "🔒 Plugins & Privacy")

        # Tab 5: Performance & Telemetry
        t5 = QWidget()
        l5 = QFormLayout(t5)
        l5.setContentsMargins(12, 12, 12, 12)

        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(2, 16)
        self.spin_workers.setValue(4)
        l5.addRow("Worker Thread Pool Size:", self.spin_workers)

        self.spin_cache = QSpinBox()
        self.spin_cache.setRange(64, 2048)
        self.spin_cache.setValue(512)
        l5.addRow("RAG Vector Cache Limit (MB):", self.spin_cache)

        self.tabs.addTab(t5, "🚀 Performance")

        layout.addWidget(self.tabs)

        # Footer Actions
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QPushButton("Save Preferences")
        self.btn_save.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: 600; padding: 6px 16px;")
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)
