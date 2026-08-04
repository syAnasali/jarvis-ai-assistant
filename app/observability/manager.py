"""Observability Manager coordinating metrics, tracing, timeline, persistence, exporters, and dashboard API."""

from typing import Any, Dict, List, Optional, Tuple
from app.core.logger import JarvisLogger
from app.observability.dashboard import HealthDashboardAPI
from app.observability.exporters import TelemetryExporterImpl
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.models import Span, SubsystemName, TimelineEvent
from app.observability.repository import SQLiteMetricsRepository
from app.observability.timeline import EventTimelineRecorder
from app.observability.tracing import DistributedTracer

logger = JarvisLogger.get_logger("observability_manager")


class ObservabilityManager:
    """Central orchestrator for the Observability & Developer Console Subsystem."""

    def __init__(
        self,
        db_path: str = "data/jarvis.db",
        persistence_enabled: bool = True,
        metrics: Optional[RuntimeMetricsCollector] = None,
        tracer: Optional[DistributedTracer] = None,
        timeline: Optional[EventTimelineRecorder] = None,
        repository: Optional[SQLiteMetricsRepository] = None,
        plugin_manager: Optional[Any] = None,
        voice_pipeline: Optional[Any] = None,
        vision_pipeline: Optional[Any] = None,
        planner_manager: Optional[Any] = None,
        knowledge_manager: Optional[Any] = None
    ) -> None:
        self.persistence_enabled = persistence_enabled
        self.metrics = metrics or RuntimeMetricsCollector()
        self.tracer = tracer or DistributedTracer()
        self.timeline = timeline or EventTimelineRecorder()
        self.repository = repository or (SQLiteMetricsRepository(db_path=db_path) if persistence_enabled else None)
        self.exporter = TelemetryExporterImpl(
            metrics=self.metrics,
            tracer=self.tracer,
            timeline=self.timeline
        )
        self.dashboard = HealthDashboardAPI(
            metrics=self.metrics,
            tracer=self.tracer,
            timeline=self.timeline,
            plugin_manager=plugin_manager,
            voice_pipeline=voice_pipeline,
            vision_pipeline=vision_pipeline,
            planner_manager=planner_manager,
            knowledge_manager=knowledge_manager
        )

        self._is_initialized = True
        logger.info("ObservabilityManager initialized successfully.")

    def start_trace(
        self,
        subsystem: SubsystemName,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Span]:
        """Starts a new trace/span and returns (trace_id, span)."""
        t_id = trace_id or self.tracer.generate_trace_id()
        span = self.tracer.start_span(
            trace_id=t_id,
            subsystem=subsystem,
            name=name,
            parent_span_id=parent_span_id,
            attributes=attributes
        )
        return t_id, span

    def end_span(self, span: Span, status: str = "OK", error_message: Optional[str] = None) -> Span:
        """Ends an active span and optionally persists it to SQLite."""
        ended = self.tracer.end_span(span, status=status, error_message=error_message)
        if self.persistence_enabled and self.repository:
            try:
                self.repository.save_span(ended)
            except Exception as e:
                logger.error(f"Failed to persist span: {e}")
        return ended

    def record_metric(
        self,
        subsystem: SubsystemName,
        metric_name: str,
        value: float,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Records a metric sample and optionally persists it to SQLite."""
        self.metrics.record(subsystem, metric_name, value, unit=unit, tags=tags)

    def record_timeline_event(
        self,
        trace_id: str,
        subsystem: SubsystemName,
        event_type: str,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TimelineEvent:
        """Records a step event in the timeline and optionally persists it to SQLite."""
        evt = self.timeline.record_event(trace_id, subsystem, event_type, duration_ms=duration_ms, metadata=metadata)
        if self.persistence_enabled and self.repository:
            try:
                self.repository.save_timeline_event(evt)
            except Exception as e:
                logger.error(f"Failed to persist timeline event: {e}")
        return evt

    def export(self, format_type: str, destination_path: str) -> str:
        """Exports telemetry diagnostics in JSON, CSV, or Markdown format."""
        fmt = format_type.lower()
        if fmt == "json":
            return self.exporter.export_json(destination_path)
        elif fmt == "csv":
            return self.exporter.export_csv(destination_path)
        elif fmt in ("markdown", "md"):
            return self.exporter.export_markdown(destination_path)
        else:
            raise ValueError(f"Unsupported export format '{format_type}'. Must be json, csv, or markdown.")

    def shutdown(self) -> None:
        """Shuts down ObservabilityManager."""
        logger.info("ObservabilityManager shutdown complete.")
