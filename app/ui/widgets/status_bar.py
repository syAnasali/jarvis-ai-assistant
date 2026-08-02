"""Status Bar widget for Jarvis Desktop UI."""

from PySide6.QtWidgets import QStatusBar, QLabel
from app.ui.theme import TEXT_SECONDARY


class StatusBarWidget(QStatusBar):
    """Bottom status bar displaying provider, latency, scheduler queue depth, and lifecycle state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusbar")
        self.setSizeGripEnabled(False)
        
        # Left: Application State
        self.app_state_label = QLabel("App State: Running")
        self.app_state_label.setStyleSheet("padding-left: 5px;")
        self.addWidget(self.app_state_label)
        
        # Spacer
        self.addWidget(QLabel(" | "))
        
        # Middle-Left: Inference Provider
        self.provider_label = QLabel("Provider: Ollama (qwen3:8b)")
        self.addWidget(self.provider_label)
        
        # Spacer
        self.addWidget(QLabel(" | "))
        
        # Middle-Right: Scheduler Queue Depth
        self.queue_label = QLabel("Scheduler Queue: 0")
        self.addWidget(self.queue_label)
        
        # Spacer
        self.addWidget(QLabel(" | "))
        
        # Right: Response Latency
        self.latency_label = QLabel("Latency: N/A")
        self.addWidget(self.latency_label)

    def update_application_state(self, state: str) -> None:
        self.app_state_label.setText(f"App State: {state}")

    def update_provider_info(self, provider_name: str, model_name: str) -> None:
        self.provider_label.setText(f"Provider: {provider_name} ({model_name})")

    def update_queue_depth(self, depth: int) -> None:
        self.queue_label.setText(f"Scheduler Queue: {depth}")

    def update_latency(self, latency_ms: float) -> None:
        self.latency_label.setText(f"Latency: {latency_ms:.2f}ms")
