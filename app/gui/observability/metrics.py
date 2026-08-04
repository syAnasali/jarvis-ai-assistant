"""MetricsGridWidget displaying live telemetry metrics cards."""

from typing import Dict, Optional
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class MetricsGridWidget(QFrame):
    """Telemetry counters card grid presenting active requests, tokens/sec, latency, RAM, and CPU usage."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        self.lbl_tokens = self._create_card(layout, "Tokens / sec", "42.8 t/s", "#6366f1")
        self.lbl_latency = self._create_card(layout, "Avg Latency", "124 ms", "#38bdf8")
        self.lbl_active_req = self._create_card(layout, "Active Requests", "2", "#818cf8")
        self.lbl_queue = self._create_card(layout, "Queue Depth", "0", "#34d399")
        self.lbl_ram = self._create_card(layout, "RAM Usage", "148 MB", "#f43f5e")
        self.lbl_cpu = self._create_card(layout, "CPU Load", "12%", "#fbbf24")

    def _create_card(self, parent_layout: QHBoxLayout, title: str, val: str, color: str) -> QLabel:
        card = QWidget()
        v_layout = QVBoxLayout(card)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        v_layout.addWidget(lbl_title)

        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {color};")
        v_layout.addWidget(lbl_val)

        parent_layout.addWidget(card)
        return lbl_val

    def update_metrics(self, metrics: Dict[str, str]) -> None:
        """Updates telemetry counter labels."""
        if "tokens_per_sec" in metrics:
            self.lbl_tokens.setText(metrics["tokens_per_sec"])
        if "avg_latency" in metrics:
            self.lbl_latency.setText(metrics["avg_latency"])
        if "active_requests" in metrics:
            self.lbl_active_req.setText(metrics["active_requests"])
        if "queue_depth" in metrics:
            self.lbl_queue.setText(metrics["queue_depth"])
        if "ram_usage" in metrics:
            self.lbl_ram.setText(metrics["ram_usage"])
        if "cpu_load" in metrics:
            self.lbl_cpu.setText(metrics["cpu_load"])
