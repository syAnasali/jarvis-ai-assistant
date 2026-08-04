"""Diagnostic script testing full ObservabilityManager subsystem integration."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.observability.manager import ObservabilityManager
from app.observability.models import SubsystemName


def main() -> None:
    print("==================================================")
    print("Testing Observability Manager Diagnostics")
    print("==================================================")

    mgr = ObservabilityManager(persistence_enabled=False)

    # Start trace
    t_id, span = mgr.start_trace(SubsystemName.LLM, "llm_generate")
    mgr.record_metric(SubsystemName.LLM, "requests", 1.0)
    mgr.record_timeline_event(t_id, SubsystemName.LLM, "LLM Request Started")
    mgr.end_span(span)

    # Check dashboard API
    report = mgr.dashboard.health_report()
    print(f"Health Status: overall='{report['overall_status']}', active_requests={report['active_requests']}")

    assert report["overall_status"] == "ok"
    print("PASS: ObservabilityManager integration verified.")

    mgr.shutdown()
    print("PASS: ObservabilityManager shutdown complete.")
    print("\nALL OBSERVABILITY DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
