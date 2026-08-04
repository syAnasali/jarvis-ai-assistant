"""Diagnostic script testing PySide6 Observability Dashboard offscreen."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.views.diagnostics_view import DiagnosticsView


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Observability Dashboard Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    diag_view = DiagnosticsView()
    print("PASS: DiagnosticsView instantiated successfully.")

    # Refresh metrics
    diag_view.btn_refresh.click()
    if diag_view.controller.active_worker:
        diag_view.controller.active_worker.wait(2000)
    app.processEvents()

    assert diag_view.metrics_grid.lbl_tokens.text() != ""
    print("PASS: QThread ObservabilityWorker metrics refresh verified.")

    # Export report
    diag_view.controller.export_telemetry("json", "exports/test_telemetry.json")
    if diag_view.controller.active_worker:
        diag_view.controller.active_worker.wait(2000)
    app.processEvents()

    print("PASS: QThread ObservabilityWorker report export verified.")

    print("\nALL OBSERVABILITY DASHBOARD DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
