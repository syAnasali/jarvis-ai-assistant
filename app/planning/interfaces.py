"""Planning subsystem interfaces and contracts."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.agent.models import AgentRequest
from app.planning.models import TaskPlan


class TaskPlanner(ABC):
    """Abstract interface defining the contract for formulating structured task plans."""

    @abstractmethod
    def create_plan(
        self,
        request: AgentRequest,
        available_tools: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]] | None = None,
        memory_context: str = ""
    ) -> TaskPlan:
        """Formulates an executable TaskPlan based on user request, tools, history, and memory context.

        Args:
            request: The incoming user AgentRequest.
            available_tools: Schema metadata dictionaries describing the registered system tools.
            conversation_history: Optional prebuilt bounded dialogue history payload.
            memory_context: Optional prebuilt long-term memory context string.

        Returns:
            TaskPlan: The generated executable task plan.

        Raises:
            PlanningError: If plan formulation, API calling, or parsing fails.
        """
        pass
