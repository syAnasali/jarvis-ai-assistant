"""Unit tests for HealthDashboardAPI."""

import pytest
from app.observability.dashboard import HealthDashboardAPI
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.tracing import DistributedTracer
from app.observability.timeline import EventTimelineRecorder


def test_health_dashboard_api():
    metrics = RuntimeMetricsCollector()
    tracer = DistributedTracer()
    timeline = EventTimelineRecorder()

    api = HealthDashboardAPI(metrics=metrics, tracer=tracer, timeline=timeline)

    report = api.health_report()
    assert report["overall_status"] == "ok"

    active = api.active_requests()
    assert isinstance(active, list)

    summary = api.runtime_summary()
    assert "metrics" in summary
