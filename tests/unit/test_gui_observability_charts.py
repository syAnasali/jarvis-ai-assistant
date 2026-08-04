"""Unit tests for TelemetryChartsWidget."""

import os
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.gui.observability.charts import TelemetryChartsWidget


def test_telemetry_charts_widget():
    app = QApplication.instance() or QApplication([])

    charts = TelemetryChartsWidget()
    assert len(charts.latency_points) > 0

    charts._animate_step()
    assert len(charts.latency_points) > 1
