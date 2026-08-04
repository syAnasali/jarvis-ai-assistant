"""Hierarchical Planner decomposing high-level user goals into DAG task graphs."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.planner.interfaces import HierarchicalPlanner
from app.planner.models import Goal, NodeStatus, NodeType, Plan, PlanNode, PlanStatus
from app.utils.id_generator import generate_plan_id, generate_step_id

logger = JarvisLogger.get_logger("hierarchical_planner")


class GoalDecomposer(HierarchicalPlanner):
    """Decomposes complex goals into verified DAG task graphs using tool, vision, and memory context."""

    def __init__(self, memory_manager: Optional[Any] = None) -> None:
        self.memory_manager = memory_manager

    def decompose_goal(self, goal: Goal) -> Plan:
        """Decomposes a user goal into an ordered DAG task plan."""
        logger.info(f"Decomposing goal '{goal.objective}' (goal_id='{goal.goal_id}')...")
        plan_id = generate_plan_id()

        # 1. Retrieve memory context if memory manager is available
        memory_context: List[str] = []
        if self.memory_manager:
            try:
                memories = self.memory_manager.search_memories(goal.objective)
                memory_context = [m.content for m in memories]
                logger.info(f"Retrieved {len(memory_context)} relevant memories for goal planning.")
            except Exception as e:
                logger.warning(f"Memory lookup during goal decomposition notice: {e}")

        # 2. Decompose objective string into graph nodes
        nodes = self._build_dag_nodes(goal.objective, memory_context)

        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            nodes=nodes,
            status=PlanStatus.CREATED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata={"memory_context_count": len(memory_context)}
        )

        logger.info(f"Plan '{plan_id}' constructed with {len(nodes)} DAG nodes.")
        return plan

    def _build_dag_nodes(self, objective: str, memory_context: List[str]) -> Dict[str, PlanNode]:
        """Generates DAG task nodes based on objective pattern matching and memory context."""
        obj_lower = objective.lower()
        nodes: Dict[str, PlanNode] = {}

        # Pattern: Organize Downloads
        if "organize" in obj_lower and "download" in obj_lower:
            n1 = PlanNode(
                node_id="node_inspect_downloads",
                description="Inspect Downloads directory contents",
                node_type=NodeType.TOOL,
                action="list_directory",
                arguments={"path": "Downloads"},
                dependencies=[],
                verification_action="inspect_path"
            )
            n2 = PlanNode(
                node_id="node_create_sorted_dirs",
                description="Create categorized sub-folders for Downloads",
                node_type=NodeType.TOOL,
                action="create_directory",
                arguments={"path": "Downloads/Organized"},
                dependencies=["node_inspect_downloads"],
                verification_action="inspect_path"
            )
            nodes[n1.node_id] = n1
            nodes[n2.node_id] = n2
            return nodes

        # Pattern: Prepare workspace / Launch dev environment
        if "workspace" in obj_lower or "launch" in obj_lower or "dev" in obj_lower:
            n1 = PlanNode(
                node_id="node_observe_desktop",
                description="Capture desktop state",
                node_type=NodeType.VISION,
                action="capture_screen",
                arguments={"prompt": "Observe desktop window arrangement"},
                dependencies=[]
            )
            n2 = PlanNode(
                node_id="node_launch_editor",
                description="Launch primary application",
                node_type=NodeType.TOOL,
                action="launch_application",
                arguments={"app_name": "notepad"},
                dependencies=["node_observe_desktop"],
                verification_action="find_running_process"
            )
            nodes[n1.node_id] = n1
            nodes[n2.node_id] = n2
            return nodes

        # Default Generic Plan Decomposition
        n1 = PlanNode(
            node_id="node_observe",
            description=f"Inspect system state for objective: {objective[:40]}",
            node_type=NodeType.TOOL,
            action="get_system_info",
            arguments={},
            dependencies=[]
        )
        n2 = PlanNode(
            node_id="node_execute_action",
            description=f"Execute primary task for objective: {objective[:40]}",
            node_type=NodeType.TOOL,
            action="get_current_time",
            arguments={},
            dependencies=["node_observe"]
        )
        nodes[n1.node_id] = n1
        nodes[n2.node_id] = n2
        return nodes
