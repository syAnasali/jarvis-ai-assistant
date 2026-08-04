"""DiagnosticsView assembling HealthOverviewWidget, MetricsGridWidget, TelemetryChartsWidget, TraceTreeWidget, and TimelineViewWidget."""

from typing import Any, Optional
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from app.gui.observability.charts import TelemetryChartsWidget
from app.gui.observability.controller import ObservabilityController
from app.gui.observability.export import ExportTelemetryDialog
from app.gui.observability.health import HealthOverviewWidget
from app.gui.observability.metrics import MetricsGridWidget
from app.gui.observability.requests import RequestDetailsWidget
from app.gui.observability.timeline import TimelineViewWidget
from app.gui.observability.traces import TraceTreeWidget


class DiagnosticsView(QWidget):
    """Observability Dashboard interface powering live telemetry, tracing, and diagnostics."""

    def __init__(self, observability_mgr: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = ObservabilityController(observability_mgr=observability_mgr, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header & Action Toolbar
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Observability & Developer Console")
        lbl_title.setObjectName("headerTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.controller.refresh_telemetry)
        hdr_layout.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("📥 Export Telemetry")
        self.btn_export.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: 600; padding: 4px 12px;")
        self.btn_export.clicked.connect(self._on_export_clicked)
        hdr_layout.addWidget(self.btn_export)

        layout.addLayout(hdr_layout)

        # 2. Health Overview Grid (8 Subsystems)
        self.health_widget = HealthOverviewWidget(self)
        layout.addWidget(self.health_widget)

        # 3. Telemetry Counters Bar
        self.metrics_grid = MetricsGridWidget(self)
        layout.addWidget(self.metrics_grid)

        # 4. Main Splitter (Left: Trend Charts & Trace Tree | Right: Event Timeline & Inspector)
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Charts + Distributed Traces
        left_col = QWidget()
        l_layout = QVBoxLayout(left_col)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(8)

        self.charts_widget = TelemetryChartsWidget(self)
        l_layout.addWidget(self.charts_widget)

        self.trace_tree = TraceTreeWidget(self)
        l_layout.addWidget(self.trace_tree)

        splitter.addWidget(left_col)

        # Right Column: Timeline + Request Details Inspector
        right_col = QWidget()
        r_layout = QVBoxLayout(right_col)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(8)

        self.timeline_widget = TimelineViewWidget(self)
        r_layout.addWidget(self.timeline_widget)

        self.request_details = RequestDetailsWidget(self)
        r_layout.addWidget(self.request_details)

        splitter.addWidget(right_col)

        splitter.setSizes([550, 450])
        layout.addWidget(splitter)

        # Wire Signals
        self.controller.metrics_updated.connect(self.metrics_grid.update_metrics)
        self.controller.health_updated.connect(self.health_widget.update_health)

    def _on_export_clicked(self) -> None:
        dialog = ExportTelemetryDialog(parent=self)
        if dialog.exec():
            fmt, path = dialog.get_export_info()
            self.controller.export_telemetry(fmt, path)
