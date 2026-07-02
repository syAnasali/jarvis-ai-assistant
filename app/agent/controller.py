"""Agent execution orchestrator controller."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from app.agent.models import AgentRequest, AgentResponse
from app.agent.conversation import Conversation
from app.agent.context import ContextManager
from app.agent.messages import Message, MessageRole
from app.ai.manager import LLMManager
from app.ai.formatter import MessageFormatter
from app.ai.parser import ResponseParser


class AgentController:
    """Manages the communication pipeline and delegates request execution."""

    def __init__(
        self,
        conversation: Conversation,
        context_manager: ContextManager,
        llm_manager: LLMManager
    ) -> None:
        """Initializes the AgentController.

        Args:
            conversation: The active Conversation model.
            context_manager: The active session ContextManager.
            llm_manager: The LLM manager to route calls.
        """
        self.conversation = conversation
        self.context_manager = context_manager
        self._llm_manager = llm_manager
        self._formatter = MessageFormatter()
        self._parser = ResponseParser()

    def process_request(self, request: AgentRequest) -> AgentResponse:
        """Processes an incoming user request using the active context.

        Args:
            request: The input AgentRequest object.

        Returns:
            AgentResponse: The resulting agent response.
        """
        self.context_manager.set_active_request(request)

        # 1. Create and add user Message to Conversation
        user_message = Message(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            role=MessageRole.USER,
            content=request.text,
            timestamp=datetime.now(timezone.utc),
            metadata=request.metadata,
        )
        self.conversation.add_message(user_message)

        # 2. Use MessageFormatter to get payload ready for provider
        formatted_messages = self._formatter.format_history(self.conversation.get_history())

        # 3. Call LLMManager.generate()
        raw_response = self._llm_manager.generate(formatted_messages)

        # 4. Pass result to ResponseParser to create AgentResponse
        agent_response = self._parser.parse_response(raw_response)

        # 5. Create and store assistant Message
        assistant_message = Message(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            role=MessageRole.ASSISTANT,
            content=agent_response.text,
            timestamp=datetime.now(timezone.utc),
            metadata=agent_response.metadata,
        )
        self.conversation.add_message(assistant_message)

        return agent_response

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
