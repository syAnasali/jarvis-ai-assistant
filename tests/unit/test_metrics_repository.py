"""Unit tests for SQLiteMetricsRepository."""

import os
import pytest
from app.observability.repository import SQLiteMetricsRepository
from app.observability.models import MetricRecord, SubsystemName


def test_metrics_repository_persistence(tmp_path):
    db_file = str(tmp_path / "test_telemetry.db")
    repo = SQLiteMetricsRepository(db_path=db_file)

    rec = MetricRecord(subsystem=SubsystemName.KNOWLEDGE, metric_name="searches", value=4.0)
    repo.save_metric(rec)

    # Clean up old records check
    deleted = repo.cleanup_old_records(retention_days=7)
    assert isinstance(deleted, int)
