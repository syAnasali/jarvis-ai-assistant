"""StatusBarNav widget displaying live model, session, memory, plugin, and system telemetry."""

from typing import Optional
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt


class StatusBarNav(QWidget):
    """Bottom status bar displaying live backend system metrics and state."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBarWidget")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        self.lbl_model = QLabel("Model: llama3")
        self.lbl_model.setObjectName("statusLabel")

        self.lbl_provider = QLabel("Provider: ollama")
        self.lbl_provider.setObjectName("statusLabel")

        self.lbl_session = QLabel("Session: main_session")
        self.lbl_session.setObjectName("statusLabel")

        self.lbl_memory = QLabel("Memories: 0")
        self.lbl_memory.setObjectName("statusLabel")

        self.lbl_plugin = QLabel("Plugins: 4")
        self.lbl_plugin.setObjectName("statusLabel")

        self.lbl_status = QLabel("Status: Ready")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setStyleSheet("color: #10b981; font-weight: 600;")

        layout.addWidget(self.lbl_model)
        layout.addWidget(self.lbl_provider)
        layout.addWidget(self.lbl_session)
        layout.addWidget(self.lbl_memory)
        layout.addWidget(self.lbl_plugin)
        layout.addStretch()
        layout.addWidget(self.lbl_status)

    def update_telemetry(
        self,
        model: str = "llama3",
        provider: str = "ollama",
        session: str = "main_session",
        memory_count: int = 0,
        plugin_count: int = 0,
        status: str = "Ready"
    ) -> None:
        """Updates status bar label fields."""
        self.lbl_model.setText(f"Model: {model}")
        self.lbl_provider.setText(f"Provider: {provider}")
        self.lbl_session.setText(f"Session: {session}")
        self.lbl_memory.setText(f"Memories: {memory_count}")
        self.lbl_plugin.setText(f"Plugins: {plugin_count}")
        self.lbl_status.setText(f"Status: {status}")
