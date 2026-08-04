"""Unit tests for Observability domain models."""

import pytest
from datetime import datetime, timezone
from app.observability.models import (
    SubsystemName,
    SpanStatus,
    MetricRecord,
    Span,
    TimelineEvent,
)


def test_metric_record_model():
    rec = MetricRecord(subsystem=SubsystemName.LLM, metric_name="tokens", value=150.0, tags={"model": "llama3"})
    assert rec.subsystem == SubsystemName.LLM
    assert rec.metric_name == "tokens"
    assert rec.value == 150.0
    assert rec.tags["model"] == "llama3"


def test_span_model():
    s = Span(
        trace_id="t1",
        span_id="s1",
        subsystem=SubsystemName.AGENT,
        name="agent_step",
        start_time=datetime.now(timezone.utc),
        duration_ms=45.0,
        status=SpanStatus.OK
    )
    assert s.trace_id == "t1"
    assert s.duration_ms == 45.0
    assert s.status == SpanStatus.OK
