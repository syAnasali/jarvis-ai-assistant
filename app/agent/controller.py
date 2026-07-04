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
from app.agent.planner import Planner
from app.agent.executor import Executor

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
        self._planner = Planner()
        self._executor = Executor(llm_manager)

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

            # 2. Formulate Plan using Planner
            logger.info("Formulating execution plan...")
            plan = self._planner.create_plan(request)
            logger.info(f"Intent classified: {plan.intent.intent_type.name} (confidence={plan.intent.confidence})")
            logger.info(f"Execution Plan: use_llm={plan.use_llm}, use_tools={plan.use_tools}, use_memory={plan.use_memory}")

            # 3. Use MessageFormatter to get payload ready
            logger.info("Formatting started.")
            formatted_messages = self._formatter.format_history(self.conversation.get_history())

            # 4. Run Plan using Executor
            logger.info("Executing plan...")
            raw_response = self._executor.execute(plan, formatted_messages)
            logger.info("Execution complete, response received.")

            # 5. Pass result to ResponseParser to create AgentResponse
            agent_response = self._parser.parse_response(raw_response)
            logger.info("Response parsing complete.")

            # 6. Create and store assistant Message
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
