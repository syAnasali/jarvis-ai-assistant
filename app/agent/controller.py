"""Agent execution orchestrator controller."""

import time
from datetime import datetime, timezone
from typing import Dict, Any
from app.agent.models import AgentRequest, AgentResponse
from app.agent.conversation import Conversation
from app.agent.context import ContextManager
from app.agent.messages import Message, MessageRole
from app.ai.manager import LLMManager
from app.ai.formatter import MessageFormatter
from app.ai.parser import ResponseParser
from app.core.logger import JarvisLogger
from app.utils.id_generator import generate_message_id

logger = JarvisLogger.get_logger("agent_controller")


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
        start_time = time.perf_counter()
        logger.info(f"Request received: ID={request.request_id}")

        try:
            self.context_manager.set_active_request(request)

            # 1. Create and add user Message to Conversation
            user_message = Message(
                id=generate_message_id(),
                role=MessageRole.USER,
                content=request.text,
                timestamp=datetime.now(timezone.utc),
                metadata=request.metadata,
            )
            self.conversation.add_message(user_message)
            logger.info("Conversation updated with user message.")

            # 2. Use MessageFormatter to get payload ready for provider
            logger.info("Formatting started.")
            formatted_messages = self._formatter.format_history(self.conversation.get_history())

            # 3. Call LLMManager.generate()
            logger.info("LLM request sent.")
            raw_response = self._llm_manager.generate(formatted_messages)
            logger.info("LLM response received.")

            # 4. Pass result to ResponseParser to create AgentResponse
            agent_response = self._parser.parse_response(raw_response)
            logger.info("Response parsing complete.")

            # 5. Create and store assistant Message
            assistant_message = Message(
                id=generate_message_id(),
                role=MessageRole.ASSISTANT,
                content=agent_response.text,
                timestamp=datetime.now(timezone.utc),
                metadata=agent_response.metadata,
            )
            self.conversation.add_message(assistant_message)
            logger.info("Assistant response stored.")

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Request completed. Execution time: {duration_ms:.2f} ms")

            return agent_response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error processing request: {e}. Execution time: {duration_ms:.2f} ms")
            raise
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
