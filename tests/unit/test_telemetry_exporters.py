"""Unit tests for TelemetryExporterImpl."""

import os
import pytest
from app.observability.exporters import TelemetryExporterImpl
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.tracing import DistributedTracer
from app.observability.timeline import EventTimelineRecorder


def test_telemetry_exporter_formats(tmp_path):
    metrics = RuntimeMetricsCollector()
    tracer = DistributedTracer()
    timeline = EventTimelineRecorder()

    exporter = TelemetryExporterImpl(metrics=metrics, tracer=tracer, timeline=timeline)

    j_path = str(tmp_path / "exp.json")
    c_path = str(tmp_path / "exp.csv")
    m_path = str(tmp_path / "exp.md")

    exporter.export_json(j_path)
    exporter.export_csv(c_path)
    exporter.export_markdown(m_path)

    assert os.path.exists(j_path)
    assert os.path.exists(c_path)
    assert os.path.exists(m_path)
