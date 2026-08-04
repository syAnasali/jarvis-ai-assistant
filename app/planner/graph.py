"""TaskGraph Directed Acyclic Graph (DAG) structure and topological dependency resolver."""

from typing import Dict, List, Set, Tuple
from app.core.exceptions import JarvisError
from app.planner.models import NodeStatus, PlanNode


class GraphCycleError(JarvisError):
    """Raised when a task graph contains a circular dependency cycle."""
    pass


class TaskGraph:
    """Manages DAG dependency resolution, topological sorting, and execution readiness."""

    def __init__(self, nodes: Dict[str, PlanNode]) -> None:
        self.nodes: Dict[str, PlanNode] = dict(nodes)
        self.validate_dag()

    def validate_dag(self) -> None:
        """Validates that the task graph is acyclic and dependencies are valid."""
        # 1. Validate dependency reference existence
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"Node '{node_id}' references unknown dependency node '{dep}'.")

        # 2. Cycle detection via DFS depth coloring
        visited: Dict[str, int] = {nid: 0 for nid in self.nodes}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(nid: str) -> None:
            visited[nid] = 1
            node = self.nodes[nid]
            for dep_id in node.dependencies:
                if visited[dep_id] == 1:
                    raise GraphCycleError(f"Cycle detected in task graph involving node '{dep_id}'.")
                if visited[dep_id] == 0:
                    dfs(dep_id)
            visited[nid] = 2

        for nid in self.nodes:
            if visited[nid] == 0:
                dfs(nid)

    def get_ready_nodes(self) -> List[PlanNode]:
        """Returns nodes whose dependencies are all COMPLETED and status is PENDING."""
        ready: List[PlanNode] = []
        for node_id, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue

            # All dependencies must be COMPLETED or SKIPPED
            deps_satisfied = True
            for dep_id in node.dependencies:
                dep_node = self.nodes[dep_id]
                if dep_node.status not in (NodeStatus.COMPLETED, NodeStatus.SKIPPED):
                    deps_satisfied = False
                    break

            if deps_satisfied:
                ready.append(node)

        return ready

    def topological_sort(self) -> List[PlanNode]:
        """Returns nodes in topological dependency execution order."""
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in self.nodes}

        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                adj[dep].append(node_id)
                in_degree[node_id] += 1

        queue: List[str] = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_nodes: List[PlanNode] = []

        while queue:
            curr = queue.pop(0)
            sorted_nodes.append(self.nodes[curr])
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        return sorted_nodes

    def update_node(self, updated_node: PlanNode) -> None:
        """Updates a node in the graph."""
        self.nodes[updated_node.node_id] = updated_node

    def is_complete(self) -> bool:
        """Checks if all nodes are in terminal state (COMPLETED, SKIPPED, or ROLLED_BACK)."""
        return all(
            node.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED, NodeStatus.ROLLED_BACK)
            for node in self.nodes.values()
        )

    def is_failed(self) -> bool:
        """Checks if any node has failed without recovery."""
        return any(node.status == NodeStatus.FAILED for node in self.nodes.values())
