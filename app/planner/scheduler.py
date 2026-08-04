"""Task Scheduler handling DAG node branch execution and queueing."""

import queue
from typing import List, Optional
from app.core.logger import JarvisLogger
from app.planner.graph import TaskGraph
from app.planner.models import PlanNode

logger = JarvisLogger.get_logger("task_scheduler")


class TaskScheduler:
    """Schedules ready DAG task nodes across parallel branches or sequential queues."""

    def __init__(self, max_concurrent: int = 4) -> None:
        self.max_concurrent = max_concurrent
        self._task_queue: queue.Queue = queue.Queue()

    def schedule_ready_nodes(self, graph: TaskGraph) -> List[PlanNode]:
        """Inspects TaskGraph and enqueues executable ready nodes."""
        ready_nodes = graph.get_ready_nodes()
        logger.info(f"Scheduling {len(ready_nodes)} ready nodes for graph execution.")
        for node in ready_nodes:
            self._task_queue.put(node)
        return ready_nodes

    def next_task(self) -> Optional[PlanNode]:
        """Retrieves next scheduled node from execution queue."""
        try:
            return self._task_queue.get_nowait()
        except queue.Empty:
            return None

    def clear(self) -> None:
        """Clears scheduled task queue."""
        with self._task_queue.mutex:
            self._task_queue.queue.clear()
