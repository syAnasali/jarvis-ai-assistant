"""Unit tests for RuntimeMetricsCollector."""

import pytest
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.models import SubsystemName


def test_metrics_collector_aggregation():
    collector = RuntimeMetricsCollector()

    collector.increment(SubsystemName.MEMORY, "retrieval_count", 2)
    collector.increment(SubsystemName.MEMORY, "retrieval_count", 3)
    collector.observe(SubsystemName.VISION, "ocr_duration", 350.0)

    summary = collector.get_summary()

    assert summary["memory"]["retrieval_count"] == 5.0
    assert summary["vision"]["ocr_duration"] == 350.0
