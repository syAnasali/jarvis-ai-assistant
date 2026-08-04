"""Distributed Tracer managing request trace IDs, parent/child span hierarchies, and latencies."""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.observability.interfaces import Tracer
from app.observability.models import Span, SpanStatus, SubsystemName

logger = JarvisLogger.get_logger("observability_tracer")


class DistributedTracer(Tracer):
    """Thread-safe tracer managing spans and trace context propagation."""

    def __init__(self) -> None:
        self._active_spans: Dict[str, Span] = {}
        self._completed_spans: List[Span] = []
        self._lock = threading.Lock()

    def generate_trace_id(self) -> str:
        """Generates a new unique trace ID."""
        return f"trace_{uuid.uuid4().hex[:12]}"

    def generate_span_id(self) -> str:
        """Generates a new unique span ID."""
        return f"span_{uuid.uuid4().hex[:8]}"

    def start_span(
        self,
        trace_id: str,
        subsystem: SubsystemName,
        name: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Starts a new tracing span."""
        span_id = self.generate_span_id()
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            subsystem=subsystem,
            name=name,
            start_time=datetime.now(timezone.utc),
            status=SpanStatus.UNSET,
            attributes=attributes or {}
        )

        with self._lock:
            self._active_spans[span_id] = span

        logger.debug(f"Started span '{name}' (span_id='{span_id}', trace_id='{trace_id}').")
        return span

    def end_span(self, span: Span, status: str = "OK", error_message: Optional[str] = None) -> Span:
        """Ends an active tracing span and computes duration."""
        now = datetime.now(timezone.utc)
        duration_ms = (now - span.start_time).total_seconds() * 1000.0

        st_enum = SpanStatus.OK if status.upper() == "OK" else SpanStatus.ERROR

        ended_span = Span(
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            subsystem=span.subsystem,
            name=span.name,
            start_time=span.start_time,
            end_time=now,
            duration_ms=round(duration_ms, 2),
            status=st_enum,
            attributes=dict(span.attributes),
            error_message=error_message
        )

        with self._lock:
            if span.span_id in self._active_spans:
                del self._active_spans[span.span_id]
            self._completed_spans.append(ended_span)

        logger.debug(f"Ended span '{span.name}' (duration={ended_span.duration_ms}ms, status={st_enum.value}).")
        return ended_span

    def get_spans_for_trace(self, trace_id: str) -> List[Span]:
        """Retrieves all completed spans for a given trace_id."""
        with self._lock:
            return [s for s in self._completed_spans if s.trace_id == trace_id]

    def get_all_completed_spans(self, limit: int = 100) -> List[Span]:
        """Retrieves completed spans up to limit."""
        with self._lock:
            return list(self._completed_spans[-limit:])

    def clear(self) -> None:
        """Clears in-memory active and completed spans."""
        with self._lock:
            self._active_spans.clear()
            self._completed_spans.clear()
