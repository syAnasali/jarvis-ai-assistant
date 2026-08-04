"""PlannerView assembling DagGraphWidget, ProgressTrackerWidget, ExecutionTimelineWidget, and LiveExecutionLogsWidget."""

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
from app.gui.planner.controller import PlannerController
from app.gui.planner.execution import LiveExecutionLogsWidget
from app.gui.planner.graph import DagGraphWidget
from app.gui.planner.progress import ProgressTrackerWidget
from app.gui.planner.recovery import RecoveryPanelWidget
from app.gui.planner.timeline import ExecutionTimelineWidget
from app.gui.planner.widgets import PlanMetricsWidget


class PlannerView(QWidget):
    """Planner Dashboard interface powering Autonomous Hierarchical Planning visualization."""

    def __init__(self, planner_manager: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = PlannerController(planner_manager=planner_manager, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header & Controls Toolbar
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Autonomous Hierarchical Planner Dashboard")
        lbl_title.setObjectName("headerTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        self.btn_create = QPushButton("➕ Create Plan")
        hdr_layout.addWidget(self.btn_create)

        self.btn_execute = QPushButton("▶️ Execute Plan")
        self.btn_execute.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: 600; padding: 4px 12px;")
        self.btn_execute.clicked.connect(lambda: self.controller.execute_plan("plan_001"))
        hdr_layout.addWidget(self.btn_execute)

        self.btn_export = QPushButton("📥 Export DAG")
        hdr_layout.addWidget(self.btn_export)

        layout.addLayout(hdr_layout)

        # 2. Metrics Bar
        self.metrics_bar = PlanMetricsWidget(self)
        layout.addWidget(self.metrics_bar)

        # 3. Main Content Splitter (Left: DAG Graph & Timeline | Right: Progress, Recovery & Logs)
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: DAG Graph + Timeline
        left_col = QWidget()
        l_layout = QVBoxLayout(left_col)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(8)

        self.dag_graph = DagGraphWidget(self)
        l_layout.addWidget(self.dag_graph)

        self.timeline = ExecutionTimelineWidget(self)
        l_layout.addWidget(self.timeline)

        splitter.addWidget(left_col)

        # Right Column: Progress + Recovery + Live Logs
        right_col = QWidget()
        r_layout = QVBoxLayout(right_col)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(8)

        self.progress_tracker = ProgressTrackerWidget(self)
        r_layout.addWidget(self.progress_tracker)

        self.recovery_panel = RecoveryPanelWidget(self)
        r_layout.addWidget(self.recovery_panel)

        self.live_logs = LiveExecutionLogsWidget(self)
        r_layout.addWidget(self.live_logs)

        splitter.addWidget(right_col)

        splitter.setSizes([550, 450])
        layout.addWidget(splitter)

        # Wire Controller Signals
        self.controller.node_status_changed.connect(self._on_node_status_changed)
        self.controller.progress_changed.connect(self._on_progress_changed)
        self.controller.log_received.connect(self.live_logs.append_log)
        self.controller.plan_finished.connect(self._on_plan_finished)

        self.progress_tracker.pause_requested.connect(self.controller.pause_plan)
        self.progress_tracker.resume_requested.connect(self.controller.resume_plan)
        self.progress_tracker.cancel_requested.connect(self.controller.cancel_plan)

    def _on_node_status_changed(self, node_id: str, status: str) -> None:
        self.dag_graph.update_node_status(node_id, status)
        self.timeline.add_timeline_event("step", f"Node {node_id} status changed to {status}")

    def _on_progress_changed(self, current: int, total: int, running_task: str) -> None:
        self.progress_tracker.set_progress(current, total, running_task_name=running_task)

    def _on_plan_finished(self, plan_id: str) -> None:
        self.timeline.add_timeline_event("completion", f"Plan '{plan_id}' finished execution")
        self.metrics_bar.update_metrics(active=0, completed=9)
