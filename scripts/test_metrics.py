"""Diagnostic script testing RuntimeMetricsCollector counter aggregation."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.observability.metrics import RuntimeMetricsCollector
from app.observability.models import SubsystemName


def main() -> None:
    print("==================================================")
    print("Testing Runtime Metrics Diagnostics")
    print("==================================================")

    collector = RuntimeMetricsCollector()
    collector.increment(SubsystemName.LLM, "requests", 5.0)
    collector.observe(SubsystemName.LLM, "latency", 120.5, unit="ms")

    summary = collector.get_summary()
    print(f"Metrics Summary: {summary}")

    assert summary["llm"]["requests"] == 5.0
    assert summary["llm"]["latency"] == 120.5
    print("PASS: Runtime metrics collection & aggregation verified.")

    print("\nALL METRICS DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
