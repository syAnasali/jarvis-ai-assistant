"""Telemetry Exporter producing JSON, CSV, and Markdown diagnostic exports."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from app.core.logger import JarvisLogger
from app.observability.interfaces import TelemetryExporter
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.timeline import EventTimelineRecorder
from app.observability.tracing import DistributedTracer

logger = JarvisLogger.get_logger("observability_exporters")


class TelemetryExporterImpl(TelemetryExporter):
    """Implementation of TelemetryExporter generating JSON, CSV, and Markdown exports."""

    def __init__(
        self,
        metrics: RuntimeMetricsCollector,
        tracer: DistributedTracer,
        timeline: EventTimelineRecorder
    ) -> None:
        self.metrics = metrics
        self.tracer = tracer
        self.timeline = timeline

    def export_json(self, destination_path: str) -> str:
        """Exports telemetry summary to a JSON file."""
        p = Path(destination_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metrics": self.metrics.get_summary(),
            "spans": [
                {
                    "trace_id": s.trace_id,
                    "span_id": s.span_id,
                    "subsystem": s.subsystem.value,
                    "name": s.name,
                    "duration_ms": s.duration_ms,
                    "status": s.status.value,
                    "error": s.error_message
                }
                for s in self.tracer.get_all_completed_spans(limit=100)
            ],
            "timeline": [
                {
                    "trace_id": e.trace_id,
                    "subsystem": e.subsystem.value,
                    "event_type": e.event_type,
                    "duration_ms": e.duration_ms,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in self.timeline.get_timeline(limit=100)
            ]
        }

        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Exported JSON telemetry snapshot to '{destination_path}'.")
        return str(p.resolve())

    def export_csv(self, destination_path: str) -> str:
        """Exports metrics summary to a CSV file."""
        p = Path(destination_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        summary = self.metrics.get_summary()
        with open(p, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["subsystem", "metric_name", "value"])
            for sub, m_dict in summary.items():
                for m_name, val in m_dict.items():
                    writer.writerow([sub, m_name, val])

        logger.info(f"Exported CSV metrics snapshot to '{destination_path}'.")
        return str(p.resolve())

    def export_markdown(self, destination_path: str) -> str:
        """Exports telemetry summary to a formatted Markdown report."""
        p = Path(destination_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        summary = self.metrics.get_summary()
        spans = self.tracer.get_all_completed_spans(limit=10)
        events = self.timeline.get_timeline(limit=10)

        lines = [
            "# Jarvis Telemetry Diagnostic Report",
            "",
            "## Subsystem Metrics",
            ""
        ]

        for sub, m_dict in summary.items():
            lines.append(f"### Subsystem: `{sub}`")
            if m_dict:
                for k, v in m_dict.items():
                    lines.append(f"- **{k}**: {v}")
            else:
                lines.append("- *No metrics recorded*")
            lines.append("")

        lines.extend([
            "## Recent Tracing Spans",
            "",
            "| Trace ID | Span Name | Subsystem | Duration (ms) | Status |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])

        for s in spans:
            lines.append(f"| `{s.trace_id}` | `{s.name}` | `{s.subsystem.value}` | `{s.duration_ms}` | `{s.status.value}` |")

        lines.extend([
            "",
            "## Recent Timeline Events",
            "",
            "| Timestamp | Trace ID | Subsystem | Event Type | Duration (ms) |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])

        for e in events:
            lines.append(f"| `{e.timestamp.strftime('%H:%M:%S')}` | `{e.trace_id}` | `{e.subsystem.value}` | `{e.event_type}` | `{e.duration_ms}` |")

        p.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Exported Markdown telemetry report to '{destination_path}'.")
        return str(p.resolve())
