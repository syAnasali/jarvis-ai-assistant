"""Unit tests for ObservabilityController."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.observability.controller import ObservabilityController


def test_observability_controller_refresh():
    app = QApplication.instance() or QApplication([])

    ctrl = ObservabilityController()
    metrics_received = []
    ctrl.metrics_updated.connect(lambda m: metrics_received.append(m))

    ctrl.refresh_telemetry()
    if ctrl.active_worker:
        ctrl.active_worker.wait(2000)
    app.processEvents()

    assert len(metrics_received) > 0
    assert "tokens_per_sec" in metrics_received[0]
