"""Diagnostic script testing DistributedTracer span creation and duration tracking."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

import time
from app.observability.models import SpanStatus, SubsystemName
from app.observability.tracing import DistributedTracer


def main() -> None:
    print("==================================================")
    print("Testing Distributed Tracing Diagnostics")
    print("==================================================")

    tracer = DistributedTracer()
    t_id = tracer.generate_trace_id()
    span = tracer.start_span(t_id, SubsystemName.AGENT, "agent_turn")

    time.sleep(0.05)
    ended = tracer.end_span(span, status="OK")

    print(f"Span Duration: {ended.duration_ms}ms, Status: {ended.status.value}")

    assert ended.duration_ms >= 40.0
    assert ended.status == SpanStatus.OK
    print("PASS: Distributed tracing span creation & duration tracking verified.")

    print("\nALL TRACING DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
