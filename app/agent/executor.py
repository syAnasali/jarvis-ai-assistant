"""Execution engine to run execution plans."""

from collections.abc import Iterator
from typing import List, Dict, Any
from app.agent.planner import ExecutionPlan
from app.ai.manager import LLMManager


class Executor:
    """Coordinates execution of plans by calling appropriate subsystems."""

    def __init__(self, llm_manager: LLMManager) -> None:
        """Initializes the Executor.

        Args:
            llm_manager: The active LLMManager to coordinate AI calls.
        """
        self._llm_manager = llm_manager

    def execute(self, plan: ExecutionPlan, formatted_messages: List[Dict[str, Any]]) -> Any:
        """Executes the given plan.

        Currently supports executing plans with use_llm=True.

        Args:
            plan: The ExecutionPlan to execute.
            formatted_messages: Pre-formatted conversation payload history.

        Returns:
            Any: Raw provider output.

        Raises:
            NotImplementedError: If the plan requests unsupported capabilities
                                 (e.g., tools or memory).
        """
        if plan.use_tools or plan.use_memory:
            raise NotImplementedError("Tool and Memory execution paths are not yet supported.")

        if plan.use_llm:
            return self._llm_manager.generate(formatted_messages)

        raise NotImplementedError("Plan does not contain a supported execution path.")

    def execute_stream(self, plan: ExecutionPlan, formatted_messages: List[Dict[str, Any]]) -> Iterator[Any]:
        """Executes the given plan in a streaming manner.

        Currently supports executing streaming plans with use_llm=True.

        Args:
            plan: The ExecutionPlan to execute.
            formatted_messages: Pre-formatted conversation payload history.

        Returns:
            Iterator[Any]: An iterator yielding raw provider response chunks.

        Raises:
            NotImplementedError: If the plan requests unsupported capabilities
                                 (e.g., tools or memory).
        """
        if plan.use_tools or plan.use_memory:
            raise NotImplementedError("Tool and Memory execution paths are not yet supported for streaming.")

        if plan.use_llm:
            return self._llm_manager.generate_stream(formatted_messages)

        raise NotImplementedError("Plan does not contain a supported streaming execution path.")
