"""Top Bar widget for Jarvis Desktop UI."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.ui.theme import TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_BLUE, BG_SIDEBAR, BORDER_COLOR


class TopBarWidget(QFrame):
    """Top bar panel showing application branding, model, status, and microphone state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setObjectName("topbar")
        self.setStyleSheet(f"""
            QFrame#topbar {{
                background-color: {BG_SIDEBAR};
                border-bottom: 1px solid {BORDER_COLOR};
            }}
            QLabel {{
                font-weight: 500;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        # Branding / Logo
        self.logo_label = QLabel("JARVIS")
        self.logo_label.setStyleSheet(f"color: {ACCENT_BLUE}; font-weight: 800; font-size: 16px; letter-spacing: 2px;")
        layout.addWidget(self.logo_label)
        
        layout.addStretch()
        
        # Active model status label
        self.model_label = QLabel("Model: qwen3:8b")
        self.model_label.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 0 10px;")
        layout.addWidget(self.model_label)
        
        # App running status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: #25252b; padding: 4px 8px; border-radius: 4px;")
        layout.addWidget(self.status_label)
        
        # Mic indicator (microphone state)
        self.mic_label = QLabel("🎙️ Off")
        self.mic_label.setStyleSheet(f"color: {TEXT_SECONDARY}; border: 1px solid {BORDER_COLOR}; padding: 4px 8px; border-radius: 4px;")
        layout.addWidget(self.mic_label)

    def set_status(self, text: str, color_hex: str = TEXT_PRIMARY) -> None:
        """Sets the current status label text and color."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color_hex}; background: #25252b; padding: 4px 8px; border-radius: 4px;")

    def set_model(self, model_name: str) -> None:
        """Updates active model label."""
        self.model_label.setText(f"Model: {model_name}")

    def update_mic_indicator(self, active: bool, status_text: str = "") -> None:
        """Toggles mic label colors and indicators."""
        if active:
            txt = f"🎙️ {status_text}" if status_text else "🎙️ ON"
            self.mic_label.setText(txt)
            self.mic_label.setStyleSheet("color: white; background: #ef476f; padding: 4px 8px; border-radius: 4px;")
        else:
            self.mic_label.setText("🎙️ Off")
            self.mic_label.setStyleSheet(f"color: {TEXT_SECONDARY}; border: 1px solid {BORDER_COLOR}; padding: 4px 8px; border-radius: 4px;")
