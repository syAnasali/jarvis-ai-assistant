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
from app.utils.id_generator import generate_message_id, generate_response_id
from app.agent.planner import Planner, ExecutionPlan
from app.agent.executor import Executor
from app.agent.runner import AgentRunner
from app.memory.interfaces import MemoryRetriever
from app.memory.context import MemoryContextBuilder

logger = JarvisLogger.get_logger("agent_controller")


class AgentController:
    """Manages the communication pipeline and delegates request execution."""

    def __init__(
        self,
        conversation: Conversation,
        context_manager: ContextManager,
        llm_manager: LLMManager,
        agent_runner: AgentRunner | None = None,
        retriever: MemoryRetriever | None = None,
        context_builder: MemoryContextBuilder | None = None
    ) -> None:
        """Initializes the AgentController.

        Args:
            conversation: The active Conversation model.
            context_manager: The active session ContextManager.
            llm_manager: The LLM manager to route calls.
            agent_runner: The AgentRunner to orchestrate tool calling loops.
            retriever: Optional MemoryRetriever implementation.
            context_builder: Optional MemoryContextBuilder implementation.
        """
        self.conversation = conversation
        self.context_manager = context_manager
        self._llm_manager = llm_manager
        self._formatter = MessageFormatter()
        self._parser = ResponseParser()
        self._planner = Planner()
        self._executor = Executor(llm_manager)
        self._runner = agent_runner
        self._retriever = retriever
        self._context_builder = context_builder

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

            # Memory retrieval logic
            memory_matches_ids = ()
            memory_duration_ms = 0.0
            memory_context = ""

            if self._retriever is not None and self._context_builder is not None:
                mem_start = time.perf_counter()
                try:
                    ret_result = self._retriever.retrieve(request.text)
                    memory_matches_ids = tuple(m.memory.memory_id for m in ret_result.matches)
                    memory_context = self._context_builder.build(list(ret_result.matches))
                    memory_duration_ms = (time.perf_counter() - mem_start) * 1000
                    
                    logger.info(
                        f"Memory retrieval completed: "
                        f"candidates={ret_result.total_candidates}, "
                        f"selected={ret_result.selected_count}, "
                        f"duration_ms={memory_duration_ms:.2f}"
                    )
                    logger.debug(f"Selected memory IDs: {memory_matches_ids}")
                except Exception as me:
                    logger.error(f"Memory retrieval failed: {me}")
                    raise

            exec_metrics = None
            if plan.use_llm and self._runner is not None:
                logger.info("Executing via AgentRunner action loop...")
                run_result = self._runner.run(request, formatted_messages, memory_context=memory_context)
                
                # Merge the memory retrieval diagnostics into execution metrics
                from dataclasses import replace
                exec_metrics = replace(
                    run_result.execution_metrics,
                    memory_matches=memory_matches_ids,
                    memory_retrieval_duration_ms=memory_duration_ms
                )
                
                agent_response = AgentResponse(
                    response_id=generate_response_id(),
                    text=run_result.text,
                    tool_calls=[],
                    success=True,
                    metadata={"execution_metrics": exec_metrics}
                )
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
            
            if exec_metrics is not None:
                logger.info(
                    f"Request completed: "
                    f"request_id={request.request_id}, "
                    f"total_duration_ms={duration_ms:.2f}, "
                    f"agent_iterations={exec_metrics.iterations}, "
                    f"model_calls={exec_metrics.model_calls}, "
                    f"tool_calls={exec_metrics.tool_calls}"
                )
            else:
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

            # Memory retrieval logic
            memory_matches_ids = ()
            memory_duration_ms = 0.0
            memory_context = ""

            if self._retriever is not None and self._context_builder is not None:
                mem_start = time.perf_counter()
                try:
                    ret_result = self._retriever.retrieve(request.text)
                    memory_matches_ids = tuple(m.memory.memory_id for m in ret_result.matches)
                    memory_context = self._context_builder.build(list(ret_result.matches))
                    memory_duration_ms = (time.perf_counter() - mem_start) * 1000
                    
                    logger.info(
                        f"Memory retrieval completed: "
                        f"candidates={ret_result.total_candidates}, "
                        f"selected={ret_result.selected_count}, "
                        f"duration_ms={memory_duration_ms:.2f}"
                    )
                    logger.debug(f"Selected memory IDs: {memory_matches_ids}")
                except Exception as me:
                    logger.error(f"Memory retrieval failed: {me}")
                    raise

            accumulator = []
            exec_metrics = None
            if plan.use_llm and self._runner is not None:
                logger.info("Streaming execution started via AgentRunner...")
                stream = self._runner.run_stream(request, formatted_messages, memory_context=memory_context)
                
                iterator = iter(stream)
                while True:
                    try:
                        parsed_text = next(iterator)
                        if parsed_text:
                            accumulator.append(parsed_text)
                            yield parsed_text
                    except StopIteration as e:
                        from dataclasses import replace
                        exec_metrics = replace(
                            e.value,
                            memory_matches=memory_matches_ids,
                            memory_retrieval_duration_ms=memory_duration_ms
                        )
                        break
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
            
            if exec_metrics is not None:
                logger.info(
                    f"Streaming request completed: "
                    f"request_id={request.request_id}, "
                    f"total_duration_ms={duration_ms:.2f}, "
                    f"agent_iterations={exec_metrics.iterations}, "
                    f"model_calls={exec_metrics.model_calls}, "
                    f"tool_calls={exec_metrics.tool_calls}"
                )
            else:
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
