"""Diagnostic script testing TelemetryExporter JSON, CSV, and Markdown file generation."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.observability.exporters import TelemetryExporterImpl
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.models import SubsystemName
from app.observability.timeline import EventTimelineRecorder
from app.observability.tracing import DistributedTracer


def main() -> None:
    print("==================================================")
    print("Testing Telemetry Exporters Diagnostics")
    print("==================================================")

    metrics = RuntimeMetricsCollector()
    tracer = DistributedTracer()
    timeline = EventTimelineRecorder()

    metrics.record(SubsystemName.AGENT, "tool_calls", 3.0)

    exporter = TelemetryExporterImpl(metrics=metrics, tracer=tracer, timeline=timeline)

    json_path = exporter.export_json("data/scratch/test_telemetry.json")
    csv_path = exporter.export_csv("data/scratch/test_telemetry.csv")
    md_path = exporter.export_markdown("data/scratch/test_telemetry.md")

    print(f"Exported JSON: {json_path}")
    print(f"Exported CSV: {csv_path}")
    print(f"Exported Markdown: {md_path}")

    assert os.path.exists(json_path)
    assert os.path.exists(csv_path)
    assert os.path.exists(md_path)
    print("PASS: Telemetry JSON, CSV, and Markdown exports verified.")

    print("\nALL EXPORTER DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
