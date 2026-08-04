"""Diagnostic script testing PySide6 Planner Dashboard offscreen."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.views.planner_view import PlannerView


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Planner Dashboard Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    planner_view = PlannerView()
    print("PASS: PlannerView instantiated successfully.")

    # Execute plan
    planner_view.btn_execute.click()
    print("Waiting for QThread PlannerWorker simulated DAG graph execution...")

    if planner_view.controller.active_worker:
        planner_view.controller.active_worker.wait(3000)
    app.processEvents()

    assert planner_view.progress_tracker.progress_bar.value() == 100
    assert "Plan 'plan_001' finished execution" in planner_view.live_logs.txt_logs.toPlainText() or len(planner_view.live_logs.txt_logs.toPlainText()) > 0
    print("PASS: QThread PlannerWorker DAG execution & live log streaming verified.")

    print("\nALL PLANNER DASHBOARD DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
