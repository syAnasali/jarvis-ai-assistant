"""Unit tests for ObservabilityManager."""

import pytest
from app.observability.manager import ObservabilityManager
from app.observability.models import SubsystemName


def test_observability_manager_flow():
    mgr = ObservabilityManager(persistence_enabled=False)

    t_id, span = mgr.start_trace(SubsystemName.AGENT, "agent_turn")
    mgr.record_metric(SubsystemName.AGENT, "tool_calls", 2.0)
    mgr.record_timeline_event(t_id, SubsystemName.AGENT, "Tool Execution Completed", duration_ms=25.0)
    mgr.end_span(span)

    report = mgr.dashboard.health_report()
    assert report["overall_status"] == "ok"

    mgr.shutdown()
