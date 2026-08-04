"""Diagnostic script testing goal decomposition and DAG task graph construction."""

import sys
sys.path.insert(0, ".")

from app.planner.models import Goal, NodeStatus, PlanStatus
from app.planner.planner import GoalDecomposer
from app.planner.graph import TaskGraph


def main() -> None:
    print("==================================================")
    print("Testing Goal Decomposition & DAG Graph Diagnostics")
    print("==================================================")

    decomposer = GoalDecomposer()
    goal = Goal(objective="Organize my Downloads folder")

    plan = decomposer.decompose_goal(goal)
    print(f"Plan Created: plan_id={plan.plan_id}, status={plan.status.value}, nodes={len(plan.nodes)}")
    assert plan.status == PlanStatus.CREATED
    assert len(plan.nodes) >= 2
    print("PASS: Goal decomposition completed successfully.")

    graph = TaskGraph(plan.nodes)
    topo = graph.topological_sort()
    print(f"Topological Sort Order: {[n.node_id for n in topo]}")
    assert len(topo) == len(plan.nodes)
    print("PASS: Topological dependency sort verified.")

    print("\nALL GOAL DECOMPOSITION DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
