"""Diagnostic script testing plan progress calculation and progress bar rendering."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from app.planner.models import Goal, NodeStatus, NodeType, Plan, PlanNode, PlanStatus
from app.planner.graph import TaskGraph
from app.planner.progress import PlanProgressTracker


def main() -> None:
    print("==================================================")
    print("Testing Progress Tracking Diagnostics")
    print("==================================================")

    tracker = PlanProgressTracker(bar_length=10)

    n1 = PlanNode(
        node_id="n1", description="Step 1", node_type=NodeType.TOOL, action="a1", status=NodeStatus.COMPLETED
    )
    n2 = PlanNode(
        node_id="n2", description="Step 2", node_type=NodeType.TOOL, action="a2", status=NodeStatus.PENDING
    )
    nodes = {"n1": n1, "n2": n2}
    graph = TaskGraph(nodes)
    goal = Goal(objective="Progress test")
    plan = Plan(plan_id="p1", goal=goal, nodes=nodes)

    progress = tracker.calculate_progress(plan, graph)
    print(f"Calculated Progress: {progress.completed_nodes}/{progress.total_nodes} ({progress.percentage}%)")
    assert progress.completed_nodes == 1
    assert progress.total_nodes == 2
    assert progress.percentage == 50.0
    assert "[" in progress.progress_bar
    print("PASS: Progress bar rendering verified.")

    print("\nALL PROGRESS TRACKING DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
