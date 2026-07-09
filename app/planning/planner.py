"""LLM task planner implementation."""

import json
import time
from typing import Any, Dict, List
from app.agent.models import AgentRequest
from app.config.settings import settings
from app.core.exceptions import PlanningError
from app.core.logger import JarvisLogger
from app.ai.manager import LLMManager
from app.ai.models import GenerationProfile
from app.ai.scheduler import InferencePriority
from app.planning.models import TaskPlan
from app.planning.interfaces import TaskPlanner
from app.planning.prompts import PLANNER_SYSTEM_PROMPT
from app.planning.parser import PlanParser

logger = JarvisLogger.get_logger("llm_task_planner")


class LLMTaskPlanner(TaskPlanner):
    """Concrete implementation of TaskPlanner formulating plans via structured LLM calls."""

    def __init__(self, llm_manager: LLMManager, parser: PlanParser | None = None) -> None:
        """Initializes the LLMTaskPlanner.

        Args:
            llm_manager: LLMManager instance to run inference.
            parser: Optional PlanParser override.
        """
        self._llm_manager = llm_manager
        self._parser = parser or PlanParser()

    def create_plan(
        self,
        request: AgentRequest,
        available_tools: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]] | None = None,
        memory_context: str = ""
    ) -> TaskPlan:
        """Formulates an executable TaskPlan using LLM generation and JSON parsing.

        Args:
            request: The incoming user request.
            available_tools: Schema specifications for registered tools.
            conversation_history: Optional pre-trimmed dialogue context messages.
            memory_context: Optional long-term memory retrieval context.

        Returns:
            TaskPlan: The structured and parsed task plan.

        Raises:
            PlanningError: If the model call or parser fails.
        """
        start_time = time.perf_counter()
        logger.info(f"Formulating task plan for request_id={request.request_id}...")

        # 1. Format tools representation
        tools_str = ""
        if available_tools:
            tools_str = json.dumps(available_tools, indent=2)
        else:
            tools_str = "No tools available."

        # 2. Build system instructions
        system_content = PLANNER_SYSTEM_PROMPT.format(
            available_tools=tools_str,
            max_steps=settings.planning_max_steps
        )

        # 3. Formulate message payloads following system-context priority ordering
        messages: List[Dict[str, Any]] = []
        messages.append({"role": "system", "content": system_content})
        
        if memory_context:
            messages.append({"role": "system", "content": memory_context})

        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user instruction
        messages.append({"role": "user", "content": request.text})

        # 4. Generate structured JSON task plan using the PLANNING profile
        try:
            gen_result = self._llm_manager.generate(
                messages,
                profile=GenerationProfile.PLANNING,
                priority=InferencePriority.FOREGROUND
            )
        except Exception as e:
            logger.error(f"LLM model generation failed during planning: {e}")
            raise PlanningError(f"Task planning LLM execution failed: {e}") from e

        # 5. Route output to PlanParser
        try:
            from app.ai.parser import ResponseParser
            resp_parser = ResponseParser()
            parsed_resp = resp_parser.parse_response(gen_result)
            plan = self._parser.parse_plan(parsed_resp.text)
        except Exception as e:
            logger.error(f"Failed to parse task plan JSON response: {e}")
            # Ensure custom planning exceptions propagate directly
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Task plan formulated: "
            f"plan_id={plan.plan_id}, "
            f"steps={len(plan.steps)}, "
            f"duration_ms={duration_ms:.2f}"
        )
        
        # Attach the duration_ms to plan metadata
        plan.metadata["planning_duration_ms"] = duration_ms
        return plan
