"""Execution planner for deciding routing and agent workflows."""

from dataclasses import dataclass, field
from typing import Dict, Any
from app.agent.intent import Intent, IntentType
from app.agent.models import AgentRequest


@dataclass(frozen=True)
class ExecutionPlan:
    """Represents an execution plan formulated by the Planner.

    Attributes:
        intent: The classified Intent of the user request.
        use_llm: Whether execution requires an LLM inference call.
        use_tools: Whether execution requires tool execution.
        use_memory: Whether execution requires memory access.
        metadata: Additional unstructured metadata.
    """

    intent: Intent
    use_llm: bool
    use_tools: bool
    use_memory: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class Planner:
    """Formulates execution plans based on classified request intents."""

    def create_plan(self, request: AgentRequest) -> ExecutionPlan:
        """Analyzes a request and crafts a tailored ExecutionPlan.

        Currently, always defaults to a standard Chat intent requiring LLM.

        Args:
            request: The incoming AgentRequest object.

        Returns:
            ExecutionPlan: The formulated execution plan.
        """
        # Always classify as CHAT with maximum confidence for now
        intent = Intent(intent_type=IntentType.CHAT, confidence=1.0)
        
        return ExecutionPlan(
            intent=intent,
            use_llm=True,
            use_tools=False,
            use_memory=False,
            metadata={"request_id": request.request_id}
        )
