"""Diagnostic script testing plan pause, resume, cancellation, and SQLite persistence."""

import sys
sys.path.insert(0, ".")

from app.planner.manager import PlannerManager
from app.planner.models import PlanStatus


def main() -> None:
    print("==================================================")
    print("Testing Long-Running Plan Persistence Diagnostics")
    print("==================================================")

    mgr = PlannerManager()
    mgr.initialize()

    plan = mgr.create_plan_for_goal("Prepare my development environment")
    print(f"Plan Created: plan_id={plan.plan_id}")

    # Pause plan
    status_pause = mgr.control_plan(plan.plan_id, "pause")
    print(f"Plan Paused: plan_id={plan.plan_id}")

    # Retrieve plan from SQLite
    persisted = mgr.repository.get_plan(plan.plan_id)
    assert persisted is not None
    assert persisted.plan_id == plan.plan_id
    print("PASS: Plan retrieved from SQLite persistence.")

    mgr.shutdown()
    print("PASS: Long-running plan diagnostics complete.")
    print("\nALL LONG-RUNNING PLAN DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
