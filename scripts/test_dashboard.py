"""Diagnostic script testing HealthDashboardAPI status endpoints."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.observability.dashboard import HealthDashboardAPI
from app.observability.metrics import RuntimeMetricsCollector
from app.observability.timeline import EventTimelineRecorder
from app.observability.tracing import DistributedTracer


def main() -> None:
    print("==================================================")
    print("Testing Health Dashboard API Diagnostics")
    print("==================================================")

    metrics = RuntimeMetricsCollector()
    tracer = DistributedTracer()
    timeline = EventTimelineRecorder()

    api = HealthDashboardAPI(metrics=metrics, tracer=tracer, timeline=timeline)

    report = api.health_report()
    metrics_summary = api.system_metrics()

    print(f"Health Report Overall: '{report['overall_status']}'")
    assert report["overall_status"] == "ok"
    assert isinstance(metrics_summary, dict)
    print("PASS: Health Dashboard API status endpoints verified.")

    print("\nALL DASHBOARD DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
