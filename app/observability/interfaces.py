"""Abstract interface contracts for MetricsCollector, Tracer, TimelineRecorder, and TelemetryExporter."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.observability.models import MetricRecord, Span, SubsystemName, TimelineEvent


class MetricsCollector(ABC):
    """Abstract interface for metrics collection and counter aggregation."""

    @abstractmethod
    def record(self, subsystem: SubsystemName, metric_name: str, value: float, unit: str = "count", tags: Optional[Dict[str, str]] = None) -> None:
        """Records a metric sample."""
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """Returns aggregated metrics summary."""
        pass


class Tracer(ABC):
    """Abstract interface for distributed tracing span management."""

    @abstractmethod
    def start_span(self, trace_id: str, subsystem: SubsystemName, name: str, parent_span_id: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> Span:
        """Starts a new tracing span."""
        pass

    @abstractmethod
    def end_span(self, span: Span, status: str = "OK", error_message: Optional[str] = None) -> Span:
        """Ends an active tracing span."""
        pass


class TimelineRecorder(ABC):
    """Abstract interface for chronological step event timeline recording."""

    @abstractmethod
    def record_event(self, trace_id: str, subsystem: SubsystemName, event_type: str, duration_ms: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> TimelineEvent:
        """Records a step event in the chronological timeline."""
        pass

    @abstractmethod
    def get_timeline(self, trace_id: Optional[str] = None, limit: int = 50) -> List[TimelineEvent]:
        """Retrieves chronological timeline events."""
        pass


class TelemetryExporter(ABC):
    """Abstract interface for telemetry diagnostic exporters."""

    @abstractmethod
    def export_json(self, destination_path: str) -> str:
        """Exports telemetry summary to a JSON file."""
        pass

    @abstractmethod
    def export_csv(self, destination_path: str) -> str:
        """Exports telemetry summary to CSV files."""
        pass

    @abstractmethod
    def export_markdown(self, destination_path: str) -> str:
        """Exports telemetry summary to a Markdown report."""
        pass
