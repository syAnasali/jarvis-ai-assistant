"""Health Dashboard API providing diagnostic status endpoints for Phase 25 Desktop GUI."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.models import HealthStatus, SubsystemName
from app.observability.timeline import EventTimelineRecorder
from app.observability.tracing import DistributedTracer

logger = JarvisLogger.get_logger("observability_dashboard")


class HealthDashboardAPI:
    """Provides programmatic health check and diagnostic status APIs."""

    def __init__(
        self,
        metrics: RuntimeMetricsCollector,
        tracer: DistributedTracer,
        timeline: EventTimelineRecorder,
        plugin_manager: Optional[Any] = None,
        voice_pipeline: Optional[Any] = None,
        vision_pipeline: Optional[Any] = None,
        planner_manager: Optional[Any] = None,
        knowledge_manager: Optional[Any] = None
    ) -> None:
        self.metrics = metrics
        self.tracer = tracer
        self.timeline = timeline
        self.plugin_manager = plugin_manager
        self.voice_pipeline = voice_pipeline
        self.vision_pipeline = vision_pipeline
        self.planner_manager = planner_manager
        self.knowledge_manager = knowledge_manager
        self._start_time = time.time()

    def health_report(self) -> Dict[str, Any]:
        """Returns comprehensive health report across all subsystems."""
        uptime = round(time.time() - self._start_time, 2)
        subsystems = {
            "llm": {"status": "ok"},
            "agent": {"status": "ok"},
            "memory": {"status": "ok"},
            "knowledge": self.knowledge_status(),
            "planner": self.planner_status(),
            "voice": self.voice_status(),
            "vision": self.vision_status(),
            "plugin": self.plugin_status()
        }

        overall = "ok"
        for sub_name, sub_info in subsystems.items():
            if sub_info.get("status") not in ("ok", "ACTIVE", "HEALTHY"):
                if sub_info.get("status") in ("FAILED", "ERROR"):
                    overall = "degraded"

        return {
            "overall_status": overall,
            "subsystem_statuses": subsystems,
            "active_requests": len(self.active_requests()),
            "uptime_seconds": uptime,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def system_metrics(self) -> Dict[str, Any]:
        """Returns live system metrics summary."""
        return self.metrics.get_summary()

    def runtime_summary(self) -> Dict[str, Any]:
        """Returns runtime summary including recent spans and timeline events."""
        return {
            "metrics": self.metrics.get_summary(),
            "completed_spans_count": len(self.tracer.get_all_completed_spans()),
            "timeline_events_count": len(self.timeline.get_timeline()),
            "uptime_seconds": round(time.time() - self._start_time, 2)
        }

    def active_requests(self) -> List[Dict[str, Any]]:
        """Returns list of currently active tracing spans."""
        active = []
        with self.tracer._lock:
            for s_id, s in self.tracer._active_spans.items():
                active.append({
                    "trace_id": s.trace_id,
                    "span_id": s.span_id,
                    "subsystem": s.subsystem.value,
                    "name": s.name,
                    "start_time": s.start_time.isoformat()
                })
        return active

    def queue_depth(self) -> Dict[str, int]:
        """Returns queue depth metrics."""
        return {"active_traces": len(self.active_requests())}

    def plugin_status(self) -> Dict[str, Any]:
        """Returns plugin runtime status."""
        if self.plugin_manager:
            return self.plugin_manager.health_report()
        return {"status": "ok", "total_plugins": 0}

    def voice_status(self) -> Dict[str, Any]:
        """Returns voice runtime status."""
        if self.voice_pipeline:
            return self.voice_pipeline.get_status() if hasattr(self.voice_pipeline, "get_status") else {"status": "ok"}
        return {"status": "ok"}

    def vision_status(self) -> Dict[str, Any]:
        """Returns vision runtime status."""
        if self.vision_pipeline:
            return self.vision_pipeline.get_status() if hasattr(self.vision_pipeline, "get_status") else {"status": "ok"}
        return {"status": "ok"}

    def planner_status(self) -> Dict[str, Any]:
        """Returns planner subsystem status."""
        if self.planner_manager:
            return self.planner_manager.get_health_status() if hasattr(self.planner_manager, "get_health_status") else {"status": "ok"}
        return {"status": "ok"}

    def knowledge_status(self) -> Dict[str, Any]:
        """Returns RAG knowledge base status."""
        if self.knowledge_manager:
            return self.knowledge_manager.get_status() if hasattr(self.knowledge_manager, "get_status") else {"status": "ok"}
        return {"status": "ok"}
