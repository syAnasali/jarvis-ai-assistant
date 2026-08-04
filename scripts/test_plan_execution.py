"""Diagnostic script testing DAG plan execution and step delegation."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.planner.manager import PlannerManager


def main() -> None:
    print("==================================================")
    print("Testing Plan Execution Diagnostics")
    print("==================================================")

    mgr = PlannerManager()
    mgr.initialize()

    progress = mgr.run_goal("Organize my Downloads folder")
    print(f"Plan Execution Progress: {progress.completed_nodes}/{progress.total_nodes} ({progress.percentage}%)")
    assert progress.completed_nodes == progress.total_nodes
    assert progress.percentage == 100.0
    print("PASS: Plan execution completed cleanly.")

    mgr.shutdown()
    print("PASS: PlannerManager shutdown complete.")
    print("\nALL PLAN EXECUTION DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
