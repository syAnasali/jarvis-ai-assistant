"""PlanMetricsWidget and PlanCardWidget summarizing active plans and Observability metrics."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class PlanMetricsWidget(QFrame):
    """Metrics bar presenting live Observability counters for active plans, success rates, and recovery rates."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #181b26; border: 1px solid #242838; border-radius: 8px; padding: 8px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(24)

        self.lbl_active = self._create_metric_card(layout, "Active Plans", "1", "#6366f1")
        self.lbl_completed = self._create_metric_card(layout, "Completed Today", "8", "#10b981")
        self.lbl_success_rate = self._create_metric_card(layout, "Success Rate", "94.2%", "#34d399")
        self.lbl_recovery_rate = self._create_metric_card(layout, "Recovery Rate", "100%", "#818cf8")
        self.lbl_avg_duration = self._create_metric_card(layout, "Avg Duration", "4.2s", "#38bdf8")

    def _create_metric_card(self, parent_layout: QHBoxLayout, title: str, val: str, color: str) -> QLabel:
        card = QWidget()
        v_layout = QVBoxLayout(card)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        v_layout.addWidget(lbl_title)

        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {color};")
        v_layout.addWidget(lbl_val)

        parent_layout.addWidget(card)
        return lbl_val

    def update_metrics(
        self,
        active: int = 1,
        completed: int = 8,
        success_rate: str = "94.2%",
        recovery_rate: str = "100%",
        avg_duration: str = "4.2s"
    ) -> None:
        """Updates metric card values."""
        self.lbl_active.setText(str(active))
        self.lbl_completed.setText(str(completed))
        self.lbl_success_rate.setText(success_rate)
        self.lbl_recovery_rate.setText(recovery_rate)
        self.lbl_avg_duration.setText(avg_duration)


class PlanCardWidget(QFrame):
    """Summary card representing an individual plan in the dashboard sidebar."""

    def __init__(self, plan_id: str, goal: str, status: str = "RUNNING", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 6px; padding: 6px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        lbl_id = QLabel(f"📋 Plan: {plan_id}")
        lbl_id.setStyleSheet("font-weight: 600; color: #818cf8; font-size: 12px;")
        layout.addWidget(lbl_id)

        lbl_goal = QLabel(goal)
        lbl_goal.setWordWrap(True)
        lbl_goal.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        layout.addWidget(lbl_goal)

        lbl_status = QLabel(f"Status: {status}")
        lbl_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 11px;")
        layout.addWidget(lbl_status)
