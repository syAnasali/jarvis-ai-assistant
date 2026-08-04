"""SQLite Metrics Repository for durable storage of telemetry, traces, and timeline events."""

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.observability.models import MetricRecord, Span, SpanStatus, SubsystemName, TimelineEvent

logger = JarvisLogger.get_logger("observability_repository")


class SQLiteMetricsRepository:
    """SQLite repository persisting runtime metrics, distributed traces, and event timelines into data/jarvis.db."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a SQLite connection ensuring parent directory exists."""
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes SQLite telemetry tables if not existing."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observability_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subsystem TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observability_spans (
                    span_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    parent_span_id TEXT,
                    subsystem TEXT NOT NULL,
                    name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_ms REAL NOT NULL,
                    status TEXT NOT NULL,
                    attributes TEXT NOT NULL,
                    error_message TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observability_timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    subsystem TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    metadata TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
            logger.info(f"Initialized SQLite telemetry tables at '{self.db_path}'.")

    def save_metric(self, record: MetricRecord) -> None:
        """Persists a MetricRecord."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO observability_metrics (subsystem, metric_name, value, unit, tags, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.subsystem.value,
                    record.metric_name,
                    record.value,
                    record.unit,
                    json.dumps(dict(record.tags)),
                    record.timestamp.isoformat()
                )
            )
            conn.commit()

    def save_span(self, span: Span) -> None:
        """Persists a tracing Span."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO observability_spans (
                    span_id, trace_id, parent_span_id, subsystem, name,
                    start_time, end_time, duration_ms, status, attributes, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span.span_id,
                    span.trace_id,
                    span.parent_span_id,
                    span.subsystem.value,
                    span.name,
                    span.start_time.isoformat(),
                    span.end_time.isoformat() if span.end_time else None,
                    span.duration_ms,
                    span.status.value,
                    json.dumps(dict(span.attributes)),
                    span.error_message
                )
            )
            conn.commit()

    def save_timeline_event(self, event: TimelineEvent) -> None:
        """Persists a TimelineEvent."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO observability_timeline (trace_id, subsystem, event_type, duration_ms, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.trace_id,
                    event.subsystem.value,
                    event.event_type,
                    event.duration_ms,
                    json.dumps(dict(event.metadata)),
                    event.timestamp.isoformat()
                )
            )
            conn.commit()

    def query_spans(self, trace_id: Optional[str] = None, limit: int = 100) -> List[Span]:
        """Queries persisted tracing spans."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if trace_id:
                cursor.execute(
                    "SELECT * FROM observability_spans WHERE trace_id = ? ORDER BY start_time DESC LIMIT ?",
                    (trace_id, limit)
                )
            else:
                cursor.execute("SELECT * FROM observability_spans ORDER BY start_time DESC LIMIT ?", (limit,))

            rows = cursor.fetchall()
            spans: List[Span] = []
            for r in rows:
                spans.append(
                    Span(
                        trace_id=r["trace_id"],
                        span_id=r["span_id"],
                        parent_span_id=r["parent_span_id"],
                        subsystem=SubsystemName(r["subsystem"]),
                        name=r["name"],
                        start_time=datetime.fromisoformat(r["start_time"]),
                        end_time=datetime.fromisoformat(r["end_time"]) if r["end_time"] else None,
                        duration_ms=r["duration_ms"],
                        status=SpanStatus(r["status"]),
                        attributes=json.loads(r["attributes"]),
                        error_message=r["error_message"]
                    )
                )
            return spans

    def cleanup_old_records(self, retention_days: int = 7) -> int:
        """Cleans up records older than retention_days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM observability_metrics WHERE timestamp < ?", (cutoff,))
            cursor.execute("DELETE FROM observability_spans WHERE start_time < ?", (cutoff,))
            cursor.execute("DELETE FROM observability_timeline WHERE timestamp < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} telemetry records older than {retention_days} days.")
            return deleted
