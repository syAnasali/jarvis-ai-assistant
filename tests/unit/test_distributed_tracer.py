"""Unit tests for DistributedTracer."""

import pytest
from app.observability.tracing import DistributedTracer
from app.observability.models import SubsystemName, SpanStatus


def test_tracer_span_lifecycle():
    tracer = DistributedTracer()
    trace_id = tracer.generate_trace_id()

    span = tracer.start_span(trace_id, SubsystemName.PLANNER, "generate_plan")
    ended = tracer.end_span(span, status="OK")

    assert ended.trace_id == trace_id
    assert ended.status == SpanStatus.OK
    assert ended.duration_ms >= 0.0

    completed = tracer.get_spans_for_trace(trace_id)
    assert len(completed) == 1
