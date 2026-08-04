"""Runtime Metrics Collector aggregating live counters, latencies, and rates across subsystems."""

import threading
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.observability.interfaces import MetricsCollector
from app.observability.models import MetricRecord, SubsystemName

logger = JarvisLogger.get_logger("observability_metrics")


class RuntimeMetricsCollector(MetricsCollector):
    """Thread-safe collector for runtime metrics across LLM, Agent, Memory, Knowledge, Planner, Voice, Vision, and Plugin runtimes."""

    def __init__(self) -> None:
        self._records: List[MetricRecord] = []
        self._counters: Dict[str, float] = {}
        self._lock = threading.Lock()

    def record(
        self,
        subsystem: SubsystemName,
        metric_name: str,
        value: float,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Records a metric sample and updates counter aggregations."""
        rec = MetricRecord(
            subsystem=subsystem,
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags or {}
        )

        with self._lock:
            self._records.append(rec)
            key = f"{subsystem.value}.{metric_name}"
            if unit == "count":
                self._counters[key] = self._counters.get(key, 0.0) + value
            else:
                self._counters[key] = value

        logger.debug(f"Recorded metric '{key}' = {value} ({unit}).")

    def increment(self, subsystem: SubsystemName, metric_name: str, amount: float = 1.0) -> None:
        """Helper to increment a counter metric by amount."""
        self.record(subsystem, metric_name, value=amount, unit="count")

    def observe(self, subsystem: SubsystemName, metric_name: str, value: float, unit: str = "ms") -> None:
        """Helper to record a gauge or duration metric."""
        self.record(subsystem, metric_name, value=value, unit=unit)

    def get_summary(self) -> Dict[str, Any]:
        """Returns aggregated metrics summary grouped by subsystem."""
        with self._lock:
            summary: Dict[str, Dict[str, float]] = {s.value: {} for s in SubsystemName}
            for k, val in self._counters.items():
                parts = k.split(".", 1)
                sub_str = parts[0]
                m_name = parts[1]
                if sub_str in summary:
                    summary[sub_str][m_name] = val
            return summary

    def clear(self) -> None:
        """Clears all in-memory recorded metrics."""
        with self._lock:
            self._records.clear()
            self._counters.clear()
