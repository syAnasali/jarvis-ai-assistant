"""Response builder factory for generating structured AgentResponse objects."""

from typing import Dict, List, Any
from app.agent.models import AgentResponse, ToolCall


class ResponseBuilder:
    """Factory containing static helper methods to construct AgentResponse variants."""

    @staticmethod
    def success(response_id: str, text: str, metadata: Dict[str, Any] | None = None) -> AgentResponse:
        """Creates an AgentResponse representing a successful user interaction.

        Args:
            response_id: Unique identifier for the response.
            text: The text output to show or read.
            metadata: Optional additional metadata dictionary.

        Returns:
            AgentResponse: The success response.
        """
        return AgentResponse(
            response_id=response_id,
            text=text,
            success=True,
            metadata=metadata or {},
        )

    @staticmethod
    def failure(response_id: str, error_message: str, metadata: Dict[str, Any] | None = None) -> AgentResponse:
        """Creates an AgentResponse representing a failed operation.

        Args:
            response_id: Unique identifier for the response.
            error_message: Summary text explaining the error/failure.
            metadata: Optional additional metadata dictionary.

        Returns:
            AgentResponse: The failure response.
        """
        return AgentResponse(
            response_id=response_id,
            text=error_message,
            success=False,
            metadata=metadata or {},
        )

    @staticmethod
    def tool_response(
        response_id: str,
        text: str,
        tool_calls: List[ToolCall],
        metadata: Dict[str, Any] | None = None
    ) -> AgentResponse:
        """Creates an AgentResponse containing tool calls.

        Args:
            response_id: Unique identifier for the response.
            text: Explanation or accompanying message.
            tool_calls: List of requested ToolCall instances.
            metadata: Optional additional metadata dictionary.

        Returns:
            AgentResponse: The response containing tool calls.
        """
        return AgentResponse(
            response_id=response_id,
            text=text,
            tool_calls=tool_calls,
            success=True,
            metadata=metadata or {},
        )
