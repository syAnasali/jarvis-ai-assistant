"""Agent execution orchestrator controller."""

import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.agent.models import AgentRequest, AgentResponse
from app.agent.conversation import Conversation
from app.agent.context import ContextManager
from app.agent.messages import Message, MessageRole
from app.ai.manager import LLMManager
from app.ai.formatter import MessageFormatter
from app.ai.parser import ResponseParser
from app.core.logger import JarvisLogger
from app.utils.id_generator import generate_message_id
from app.agent.planner import Planner, ExecutionPlan
from app.agent.executor import Executor
from app.agent.runner import AgentRunner

logger = JarvisLogger.get_logger("agent_controller")


class AgentController:
    """Manages the communication pipeline and delegates request execution."""

    def __init__(
        self,
        conversation: Conversation,
        context_manager: ContextManager,
        llm_manager: LLMManager,
        agent_runner: AgentRunner | None = None
    ) -> None:
        """Initializes the AgentController.

        Args:
            conversation: The active Conversation model.
            context_manager: The active session ContextManager.
            llm_manager: The LLM manager to route calls.
            agent_runner: The AgentRunner to orchestrate tool calling loops.
        """
        self.conversation = conversation
        self.context_manager = context_manager
        self._llm_manager = llm_manager
        self._formatter = MessageFormatter()
        self._parser = ResponseParser()
        self._planner = Planner()
        self._executor = Executor(llm_manager)
        self._runner = agent_runner

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
            plan, formatted_messages = self._prepare_request(request)

            if plan.use_tools or plan.use_memory:
                raise NotImplementedError("Tool and Memory execution paths are not yet supported directly.")

            if plan.use_llm and self._runner is not None:
                logger.info("Executing via AgentRunner action loop...")
                agent_response = self._runner.run(request, formatted_messages)
            else:
                logger.info("Executing via Executor...")
                raw_response = self._executor.execute(plan, formatted_messages)
                agent_response = self._parser.parse_response(raw_response)

            # Create and store assistant Message
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

    def process_request_stream(self, request: AgentRequest) -> Iterator[str]:
        """Processes an incoming request as a stream of text chunks.

        Args:
            request: The input AgentRequest object.

        Returns:
            Iterator[str]: An iterator yielding text chunks.

        Raises:
            Exception: If execution fails before or during streaming.
        """
        start_time = time.perf_counter()
        logger.info(f"Streaming request received: ID={request.request_id}")

        try:
            plan, formatted_messages = self._prepare_request(request)
            logger.info("Execution plan created and conversation formatted.")

            if plan.use_tools or plan.use_memory:
                raise NotImplementedError("Tool and Memory execution paths are not yet supported for streaming.")

            accumulator = []
            if plan.use_llm and self._runner is not None:
                logger.info("Streaming execution started via AgentRunner...")
                stream = self._runner.run_stream(request, formatted_messages)
                
                for parsed_text in stream:
                    if parsed_text:
                        accumulator.append(parsed_text)
                        yield parsed_text
            else:
                logger.info("Streaming execution started via Executor...")
                stream = self._executor.execute_stream(plan, formatted_messages)
                first_chunk_received = False

                for raw_chunk in stream:
                    if not first_chunk_received:
                        logger.info("First text chunk received.")
                        first_chunk_received = True

                    parsed_text = self._parser.parse_stream_chunk(raw_chunk)
                    if parsed_text:
                        accumulator.append(parsed_text)
                        yield parsed_text

            logger.info("Streaming execution completed.")

            # Join accumulated text into the complete assistant response
            full_response_text = "".join(accumulator)

            # Create ONE assistant Message containing the complete response
            assistant_message = Message(
                id=generate_message_id(),
                role=MessageRole.ASSISTANT,
                content=full_response_text,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
            self.conversation.add_message(assistant_message)
            logger.info("Assistant response stored.")

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Streaming request completed. Total streaming duration: {duration_ms:.2f} ms")

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error processing streaming request: {e}. Execution time: {duration_ms:.2f} ms")
            # Propagate exception to caller
            raise

    def _prepare_request(self, request: AgentRequest) -> tuple[ExecutionPlan, List[Dict[str, Any]]]:
        """Prepares session state, records user input, and formats history payload.

        Args:
            request: The user AgentRequest.

        Returns:
            tuple[ExecutionPlan, List[Dict[str, Any]]]: Formulated plan and formatted history list.
        """
        self.context_manager.set_active_request(request)

        # Create and add user Message to Conversation
        user_message = Message(
            id=generate_message_id(),
            role=MessageRole.USER,
            content=request.text,
            timestamp=datetime.now(timezone.utc),
            metadata=request.metadata,
        )
        self.conversation.add_message(user_message)
        logger.info("Conversation updated with user message.")

        # Formulate Plan using Planner
        logger.info("Formulating execution plan...")
        plan = self._planner.create_plan(request)
        logger.info(f"Intent classified: {plan.intent.intent_type.name} (confidence={plan.intent.confidence})")
        logger.info(f"Execution Plan: use_llm={plan.use_llm}, use_tools={plan.use_tools}, use_memory={plan.use_memory}")

        # Use MessageFormatter to get payload ready
        logger.info("Formatting started.")
        formatted_messages = self._formatter.format_history(self.conversation.get_history())
        logger.info("Conversation formatted.")

        return plan, formatted_messages

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
