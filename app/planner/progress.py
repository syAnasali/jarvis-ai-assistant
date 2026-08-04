"""Plan progress tracker computing task progress percentages, rendering progress bars, and dispatching callbacks."""

from typing import Callable, List, Optional
from app.planner.graph import TaskGraph
from app.planner.models import NodeStatus, Plan, PlanProgress

ProgressCallback = Callable[[PlanProgress], None]


class PlanProgressTracker:
    """Computes completion progress metrics and progress bar visualizations."""

    def __init__(self, bar_length: int = 12) -> None:
        self._bar_length = bar_length
        self._callbacks: List[ProgressCallback] = []

    def register_callback(self, callback: ProgressCallback) -> None:
        """Registers a progress update listener callback."""
        self._callbacks.append(callback)

    def calculate_progress(self, plan: Plan, graph: TaskGraph, status_message: str = "") -> PlanProgress:
        """Calculates PlanProgress metrics from the current TaskGraph state."""
        total = len(graph.nodes)
        if total == 0:
            pct = 100.0
            completed = 0
            failed = 0
            active = 0
        else:
            completed = sum(1 for n in graph.nodes.values() if n.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED))
            failed = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.FAILED)
            active = sum(1 for n in graph.nodes.values() if n.status in (NodeStatus.RUNNING, NodeStatus.VERIFYING))
            pct = round((completed / total) * 100.0, 1)

        progress_bar = self._render_bar(completed, total)
        msg = status_message or f"Task {completed}/{total} {progress_bar} {int(pct)}%"

        progress = PlanProgress(
            plan_id=plan.plan_id,
            total_nodes=total,
            completed_nodes=completed,
            failed_nodes=failed,
            active_nodes=active,
            percentage=pct,
            progress_bar=progress_bar,
            status_message=msg
        )

        self._notify(progress)
        return progress

    def _render_bar(self, completed: int, total: int) -> str:
        """Renders an ASCII progress bar string like [███████░░░░]."""
        if total == 0:
            return f"[{'█' * self._bar_length}]"
        filled = int(round((completed / total) * self._bar_length))
        empty = self._bar_length - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def _notify(self, progress: PlanProgress) -> None:
        """Invokes all registered listener callbacks."""
        for cb in self._callbacks:
            try:
                cb(progress)
            except Exception:
                pass
