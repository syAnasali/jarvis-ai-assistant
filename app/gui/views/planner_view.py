"""Planner View placeholder widget."""

from typing import Optional
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class PlannerView(QWidget):
    """Placeholder view for Autonomous Hierarchical Planner DAG task graphs."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        frame = QFrame()
        frame.setObjectName("cardFrame")
        f_layout = QVBoxLayout(frame)

        lbl = QLabel("Autonomous Hierarchical Planner")
        lbl.setObjectName("headerTitle")
        lbl.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(lbl)

        sub = QLabel("DAG task graphs, node dependency trees, and real-time execution progress.")
        sub.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(sub)

        layout.addWidget(frame)
