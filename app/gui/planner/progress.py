"""ProgressTrackerWidget displaying progress bar, task metrics, and execution controls."""

from typing import Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal, Qt


class ProgressTrackerWidget(QFrame):
    """Progress tracker panel with QProgressBar and Pause/Resume/Cancel controls."""

    pause_requested = Signal()
    resume_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setStyleSheet("background-color: #1a1d29; border: 1px solid #242838; border-radius: 8px; padding: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row
        hdr_row = QHBoxLayout()
        self.lbl_task = QLabel("Running Task: Initializing DAG Graph...")
        self.lbl_task.setStyleSheet("font-weight: 600; color: #e2e8f0; font-size: 12px;")
        hdr_row.addWidget(self.lbl_task)
        hdr_row.addStretch()

        self.lbl_ratio = QLabel("0 / 0 Completed")
        self.lbl_ratio.setStyleSheet("color: #94a3b8; font-size: 11px;")
        hdr_row.addWidget(self.lbl_ratio)
        layout.addLayout(hdr_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #12141c;
                border: 1px solid #242838;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #6366f1;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Control Buttons
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.btn_pause = QPushButton("⏸️ Pause")
        self.btn_pause.setFixedHeight(28)
        self.btn_pause.clicked.connect(self.pause_requested.emit)
        ctrl_row.addWidget(self.btn_pause)

        self.btn_resume = QPushButton("▶️ Resume")
        self.btn_resume.setFixedHeight(28)
        self.btn_resume.clicked.connect(self.resume_requested.emit)
        ctrl_row.addWidget(self.btn_resume)

        self.btn_cancel = QPushButton("⏹️ Cancel")
        self.btn_cancel.setFixedHeight(28)
        self.btn_cancel.setStyleSheet("background-color: #7f1d1d; color: #ffffff;")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        ctrl_row.addWidget(self.btn_cancel)

        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

    def set_progress(self, current: int, total: int, running_task_name: str = "") -> None:
        """Updates progress bar and task label."""
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_ratio.setText(f"{current} / {total} Completed ({pct}%)")
        if running_task_name:
            self.lbl_task.setText(f"Running Task: {running_task_name}")
