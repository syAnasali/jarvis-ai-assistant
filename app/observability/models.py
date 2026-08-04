"""Immutable domain models and dataclasses for the Observability Subsystem."""

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Optional


class SubsystemName(Enum):
    """Enumeration of Jarvis core subsystems tracked by telemetry."""
    LLM = "llm"
    AGENT = "agent"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    PLANNER = "planner"
    VOICE = "voice"
    VISION = "vision"
    PLUGIN = "plugin"


class SpanStatus(Enum):
    """Status of a tracing span."""
    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


@dataclass(frozen=True)
class MetricRecord:
    """Represents an individual metric sample."""
    subsystem: SubsystemName
    metric_name: str
    value: float
    unit: str = "count"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("MetricRecord metric_name cannot be empty.")
        if self.timestamp.tzinfo is None:
            raise ValueError("MetricRecord timestamp must be timezone-aware.")
        copied_tags = MappingProxyType(copy.deepcopy(self.tags))
        object.__setattr__(self, "tags", copied_tags)


@dataclass(frozen=True)
class Span:
    """Represents a distributed tracing span."""
    trace_id: str
    span_id: str
    subsystem: SubsystemName
    name: str
    start_time: datetime
    parent_span_id: Optional[str] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.trace_id.strip():
            raise ValueError("Span trace_id cannot be empty.")
        if not self.span_id.strip():
            raise ValueError("Span span_id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Span name cannot be empty.")
        copied_attrs = MappingProxyType(copy.deepcopy(self.attributes))
        object.__setattr__(self, "attributes", copied_attrs)


@dataclass(frozen=True)
class TimelineEvent:
    """Represents a chronological step event in request processing."""
    trace_id: str
    subsystem: SubsystemName
    event_type: str
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trace_id.strip():
            raise ValueError("TimelineEvent trace_id cannot be empty.")
        if not self.event_type.strip():
            raise ValueError("TimelineEvent event_type cannot be empty.")
        if self.timestamp.tzinfo is None:
            raise ValueError("TimelineEvent timestamp must be timezone-aware.")
        copied_meta = MappingProxyType(copy.deepcopy(self.metadata))
        object.__setattr__(self, "metadata", copied_meta)


@dataclass(frozen=True)
class HealthStatus:
    """Represents overall system health status and diagnostics."""
    overall_status: str
    subsystem_statuses: Dict[str, Dict[str, Any]]
    active_requests: int
    uptime_seconds: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("HealthStatus timestamp must be timezone-aware.")
        copied_subsystems = MappingProxyType(copy.deepcopy(self.subsystem_statuses))
        object.__setattr__(self, "subsystem_statuses", copied_subsystems)


@dataclass(frozen=True)
class TelemetrySummary:
    """Aggregated snapshot summary of metrics, traces, and timeline events."""
    metrics_summary: Dict[str, Any]
    recent_spans: List[Span]
    recent_timeline: List[TimelineEvent]
    active_plugins: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        copied_metrics = MappingProxyType(copy.deepcopy(self.metrics_summary))
        copied_spans = tuple(self.recent_spans)
        copied_timeline = tuple(self.recent_timeline)
        copied_plugins = tuple(self.active_plugins)
        object.__setattr__(self, "metrics_summary", copied_metrics)
        object.__setattr__(self, "recent_spans", copied_spans)
        object.__setattr__(self, "recent_timeline", copied_timeline)
        object.__setattr__(self, "active_plugins", copied_plugins)
