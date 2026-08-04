"""Event Timeline Recorder capturing step events in request processing flows."""

import threading
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.observability.interfaces import TimelineRecorder
from app.observability.models import SubsystemName, TimelineEvent

logger = JarvisLogger.get_logger("observability_timeline")


class EventTimelineRecorder(TimelineRecorder):
    """Thread-safe recorder tracking chronological step events."""

    def __init__(self) -> None:
        self._events: List[TimelineEvent] = []
        self._lock = threading.Lock()

    def record_event(
        self,
        trace_id: str,
        subsystem: SubsystemName,
        event_type: str,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TimelineEvent:
        """Records a step event in the chronological timeline."""
        event = TimelineEvent(
            trace_id=trace_id,
            subsystem=subsystem,
            event_type=event_type,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )

        with self._lock:
            self._events.append(event)

        logger.debug(f"Recorded timeline event '{event_type}' (trace_id='{trace_id}', sub='{subsystem.value}').")
        return event

    def get_timeline(self, trace_id: Optional[str] = None, limit: int = 50) -> List[TimelineEvent]:
        """Retrieves chronological timeline events, optionally filtered by trace_id."""
        with self._lock:
            if trace_id:
                filtered = [e for e in self._events if e.trace_id == trace_id]
                return filtered[-limit:]
            return list(self._events[-limit:])

    def clear(self) -> None:
        """Clears in-memory timeline events."""
        with self._lock:
            self._events.clear()
