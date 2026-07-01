"""Agent execution orchestrator controller."""

from typing import Dict, Any
from app.agent.models import AgentRequest, AgentResponse
from app.agent.conversation import Conversation
from app.agent.context import ContextManager


class AgentController:
    """Manages the communication pipeline and delegates request execution."""

    def __init__(self, conversation: Conversation, context_manager: ContextManager) -> None:
        """Initializes the AgentController.

        Args:
            conversation: The active Conversation model.
            context_manager: The active session ContextManager.
        """
        self.conversation = conversation
        self.context_manager = context_manager

    def process_request(self, request: AgentRequest) -> AgentResponse:
        """Processes an incoming user request using the active context.

        Args:
            request: The input AgentRequest object.

        Returns:
            AgentResponse: The resulting agent response.

        Raises:
            NotImplementedError: As request processing logic is not yet implemented.
        """
        raise NotImplementedError("Request processing logic is not yet implemented.")

    def reset(self) -> None:
        """Resets the current conversation log and session state managers."""
        self.conversation.clear()
        self.context_manager.reset()

    def health_check(self) -> Dict[str, Any]:
        """Provides status validation check of the Agent Engine components.

        Returns:
            Dict[str, Any]: Health status attributes.
        """
        return {
            "status": "healthy",
            "conversation_messages_count": len(self.conversation.get_history()),
            "active_topic": self.context_manager.current_topic,
        }
