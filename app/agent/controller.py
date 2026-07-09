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
from app.conversation.manager import ConversationManager
from app.conversation.policy import ContextWindowPolicy
from app.memory.interfaces import MemoryRetriever
from app.memory.context import MemoryContextBuilder
from app.memory.coordinator import MemoryWriteCoordinator
from app.config.settings import settings

from app.planning.models import ExecutionMode
from app.planning.interfaces import TaskPlanner
from app.planning.router import ExecutionRouter
from app.planning.validator import PlanValidator
from app.planning.executor import TaskExecutor
from app.approval.models import PendingActionStatus

logger = JarvisLogger.get_logger("agent_controller")


def sanitize_for_json(obj: Any) -> Any:
    """Recursively converts non-serializable objects to JSON-serializable primitives."""
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (tuple, set)):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    elif hasattr(obj, "__dict__"):
        return sanitize_for_json(obj.__dict__)
    else:
        try:
            # Check if it has a dataclass asdict method or similar representation
            from dataclasses import is_dataclass, asdict
            if is_dataclass(obj):
                return sanitize_for_json(asdict(obj))
        except Exception:
            pass
        return str(obj)


class AgentController:
    """Manages the communication pipeline and delegates request execution."""

    def __init__(
        self,
        conversation: Conversation,
        context_manager: ContextManager,
        llm_manager: LLMManager,
        agent_runner: AgentRunner | None = None,
        retriever: MemoryRetriever | None = None,
        context_builder: MemoryContextBuilder | None = None,
        coordinator: MemoryWriteCoordinator | None = None,
        conversation_manager: ConversationManager | None = None,
        context_policy: ContextWindowPolicy | None = None,
        router: ExecutionRouter | None = None,
        planner: TaskPlanner | None = None,
        validator: PlanValidator | None = None,
        executor: TaskExecutor | None = None,
        approval_manager: Any = None
    ) -> None:
        """Initializes the AgentController.

        Args:
            conversation: The active Conversation model.
            context_manager: The active session ContextManager.
            llm_manager: The LLM manager to route calls.
            agent_runner: The AgentRunner to orchestrate tool calling loops.
            retriever: Optional MemoryRetriever implementation.
            context_builder: Optional MemoryContextBuilder implementation.
            coordinator: Optional MemoryWriteCoordinator implementation.
            conversation_manager: Optional ConversationManager implementation.
            context_policy: Optional ContextWindowPolicy implementation.
            router: Optional ExecutionRouter implementation.
            planner: Optional TaskPlanner implementation.
            validator: Optional PlanValidator implementation.
            executor: Optional TaskExecutor implementation.
            approval_manager: Optional approval manager.
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
        self._coordinator = coordinator
        self.conversation_manager = conversation_manager
        self.context_policy = context_policy
        self.active_session_id: str | None = None
        self._approval_manager = approval_manager

        # In-memory planned execution state
        self._active_plan = None
        self._active_observations = None

        # Setup planning components
        from app.planning.router import ExecutionRouter
        from app.planning.planner import LLMTaskPlanner
        from app.planning.validator import PlanValidator
        from app.planning.executor import TaskExecutor

        self._router = router or ExecutionRouter()
        self._task_planner = planner or LLMTaskPlanner(llm_manager)

        reg = getattr(agent_runner, "_registry", None)
        tool_exec = getattr(agent_runner, "_executor", None)

        self._plan_validator = validator or PlanValidator(reg)
        self._task_executor = executor or TaskExecutor(llm_manager, reg, tool_exec, self._plan_validator)

    def process_request(self, request: AgentRequest, approval_action_id: str | None = None) -> AgentResponse:
        """Processes an incoming user request using the active context.

        Args:
            request: The input AgentRequest object.
            approval_action_id: Optional ID of the approved action.

        Returns:
            AgentResponse: The resulting agent response.
        """
        start_time = time.perf_counter()
        logger.info(f"Request received: ID={request.request_id} (approval_id={approval_action_id})")

        try:
            # Check if we are handling an approval or rejection resumption
            if approval_action_id is not None and self._approval_manager is not None:
                action = self._approval_manager.get(approval_action_id)
                if not action:
                    return AgentResponse(
                        response_id=generate_response_id(),
                        text="Error: Approved action not found.",
                        success=False
                    )

                if action.status == PendingActionStatus.REJECTED:
                    # Clear active planned execution state
                    self._active_plan = None
                    self._active_observations = None
                    
                    # Create and store rejection message in history
                    agent_response = AgentResponse(
                        response_id=generate_response_id(),
                        text="Action was rejected by the user. Execution cancelled.",
                        success=False,
                        metadata={"confirmation_required": False}
                    )
                    
                    assistant_message = Message(
                        id=generate_message_id(),
                        role=MessageRole.ASSISTANT,
                        content=agent_response.text,
                        timestamp=datetime.now(timezone.utc),
                        metadata=sanitize_for_json(agent_response.metadata),
                    )
                    if self.conversation_manager and self.active_session_id:
                        self.conversation_manager.add_message(self.active_session_id, assistant_message)
                    self.conversation.add_message(assistant_message)
                    return agent_response

                if action.status == PendingActionStatus.APPROVED:
                    # If we have an active plan, resume it
                    if self._active_plan is not None:
                        logger.info("Resuming plan execution after approval...")
                        exec_result = self._task_executor.execute(
                            plan=self._active_plan,
                            original_request_text=request.text,
                            approval_action_id=approval_action_id,
                            previous_observations=self._active_observations
                        )
                        
                        from app.planning.models import PlanStatus
                        if exec_result.plan_status == PlanStatus.WAITING_APPROVAL:
                            self._active_observations = exec_result.observations
                            metadata = {
                                "execution_mode": "planned",
                                "plan_id": self._active_plan.plan_id,
                                "plan_status": exec_result.plan_status.value,
                                "steps_total": len(self._active_plan.steps),
                                "steps_completed": exec_result.steps_completed,
                                "steps_failed": exec_result.steps_failed,
                                "confirmation_required": True,
                                "pending_action_id": exec_result.metadata.get("pending_action_id"),
                                "tool_name": exec_result.metadata.get("tool_name"),
                                "reason": exec_result.metadata.get("reason")
                            }
                            agent_response = AgentResponse(
                                response_id=generate_response_id(),
                                text=exec_result.final_response,
                                success=False,
                                metadata=metadata
                            )
                        else:
                            # Plan finished or failed
                            self._active_plan = None
                            self._active_observations = None
                            
                            serialized_obs = []
                            for obs in exec_result.observations:
                                serialized_obs.append({
                                    "step_id": obs.step_id,
                                    "step_sequence": obs.step_sequence,
                                    "step_type": obs.step_type.value,
                                    "success": obs.success,
                                    "content": obs.content,
                                    "tool_name": obs.tool_name,
                                    "created_at": obs.created_at.isoformat() if obs.created_at else None
                                })
                            
                            metadata = {
                                "execution_mode": "planned",
                                "plan_id": exec_result.plan_id,
                                "plan_status": exec_result.plan_status.value,
                                "steps_total": exec_result.steps_total,
                                "steps_completed": exec_result.steps_completed,
                                "steps_failed": exec_result.steps_failed,
                                "tool_calls": exec_result.metrics.tool_calls,
                                "plan_observations": serialized_obs
                            }
                            agent_response = AgentResponse(
                                response_id=generate_response_id(),
                                text=exec_result.final_response,
                                success=exec_result.success,
                                metadata=metadata
                            )

                        assistant_message = Message(
                            id=generate_message_id(),
                            role=MessageRole.ASSISTANT,
                            content=agent_response.text,
                            timestamp=datetime.now(timezone.utc),
                            metadata=sanitize_for_json(agent_response.metadata),
                        )
                        if self.conversation_manager and self.active_session_id:
                            self.conversation_manager.add_message(self.active_session_id, assistant_message)
                        self.conversation.add_message(assistant_message)
                        return agent_response
                    
                    else:
                        # Direct mode approved execution
                        logger.info("Executing approved direct action...")
                        from app.agent.models import ToolCall
                        tool_call = ToolCall(tool_name=action.tool_name, arguments=action.arguments)
                        
                        tool_exec = getattr(self._runner, "_executor")
                        tool_result = tool_exec.execute(tool_call, approval_action_id=approval_action_id)
                        
                        import json
                        tool_content = json.dumps(tool_result.output) if tool_result.success else json.dumps({"error": tool_result.error})
                        tool_message = Message(
                            id=generate_message_id(),
                            role=MessageRole.TOOL,
                            content=tool_content,
                            timestamp=datetime.now(timezone.utc),
                            metadata={"tool_name": action.tool_name}
                        )
                        if self.conversation_manager and self.active_session_id:
                            self.conversation_manager.add_message(self.active_session_id, tool_message)
                        self.conversation.add_message(tool_message)
                        
                        # Format history without adding a duplicate user message
                        plan = self._planner.create_plan(request)
                        history = self.conversation.get_history()
                        if self.context_policy:
                            history = self.context_policy.select_history(history)
                        formatted_messages = self._formatter.format_history(history)
                        
                        # Run the remaining LLM loop
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
                            except Exception as me:
                                logger.error(f"Memory retrieval failed: {me}")
                                raise

                        run_result = self._runner.run(request, formatted_messages, memory_context=memory_context)
                        
                        from dataclasses import replace, asdict
                        exec_metrics = replace(
                            run_result.execution_metrics,
                            memory_matches=memory_matches_ids,
                            memory_retrieval_duration_ms=memory_duration_ms
                        )
                        
                        response_metadata = {
                            "execution_mode": "direct",
                            "execution_metrics": asdict(exec_metrics)
                        }
                        if run_result.confirmation_required:
                            response_metadata["confirmation_required"] = True
                            response_metadata["pending_action_id"] = run_result.pending_action_id
                            response_metadata["tool_name"] = run_result.requested_tools[0] if run_result.requested_tools else ""
                            response_metadata["reason"] = run_result.text

                        agent_response = AgentResponse(
                            response_id=generate_response_id(),
                            text=run_result.text,
                            tool_calls=[],
                            success=not run_result.confirmation_required,
                            metadata=response_metadata
                        )

                        # Create and store assistant Message
                        assistant_message = Message(
                            id=generate_message_id(),
                            role=MessageRole.ASSISTANT,
                            content=agent_response.text,
                            timestamp=datetime.now(timezone.utc),
                            metadata=sanitize_for_json(agent_response.metadata),
                        )
                        if self.conversation_manager and self.active_session_id:
                            self.conversation_manager.add_message(self.active_session_id, assistant_message)
                        self.conversation.add_message(assistant_message)
                        return agent_response

            # Standard non-resumption flow
            plan, formatted_messages = self._prepare_request(request)

            # Heuristic Routing decision
            decision = self._router.route(request)

            # Memory retrieval logic (runs for both direct and planned paths)
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
            is_planned = settings.planning_enabled and decision.mode == ExecutionMode.PLANNED

            if is_planned:
                logger.info(f"Routing to PLANNED path: confidence={decision.confidence:.2f}")

                available_tools = []
                if self._runner is not None:
                    reg = getattr(self._runner, "_registry", None)
                    if reg is not None:
                        available_tools = reg.get_schemas()

                # Exclude the current user message (last message) from the planner context history block
                history_for_planner = formatted_messages[:-1] if formatted_messages else []

                # Formulate Plan
                task_plan = self._task_planner.create_plan(
                    request=request,
                    available_tools=available_tools,
                    conversation_history=history_for_planner,
                    memory_context=memory_context
                )

                # Execute Plan step-by-step
                exec_result = self._task_executor.execute(
                    plan=task_plan,
                    original_request_text=request.text,
                    routing_confidence=decision.confidence
                )

                from app.planning.models import PlanStatus
                if exec_result.plan_status == PlanStatus.WAITING_APPROVAL:
                    # Save plan state in memory
                    self._active_plan = task_plan
                    self._active_observations = exec_result.observations
                    
                    metadata = {
                        "execution_mode": "planned",
                        "planning_confidence": decision.confidence,
                        "plan_id": task_plan.plan_id,
                        "plan_status": exec_result.plan_status.value,
                        "plan_steps": len(task_plan.steps),
                        "steps_completed": exec_result.steps_completed,
                        "steps_failed": exec_result.steps_failed,
                        "confirmation_required": True,
                        "pending_action_id": exec_result.metadata.get("pending_action_id"),
                        "tool_name": exec_result.metadata.get("tool_name"),
                        "reason": exec_result.metadata.get("reason")
                    }
                    agent_response = AgentResponse(
                        response_id=generate_response_id(),
                        text=exec_result.final_response,
                        tool_calls=[],
                        success=False,
                        metadata=metadata
                    )
                else:
                    # Safe diagnostics metadata
                    serialized_obs = []
                    for obs in exec_result.observations:
                        serialized_obs.append({
                            "step_id": obs.step_id,
                            "step_sequence": obs.step_sequence,
                            "step_type": obs.step_type.value,
                            "success": obs.success,
                            "content": obs.content,
                            "tool_name": obs.tool_name,
                            "created_at": obs.created_at.isoformat() if obs.created_at else None
                        })
                    
                    metadata = {
                        "execution_mode": "planned",
                        "planning_confidence": decision.confidence,
                        "plan_id": exec_result.plan_id,
                        "plan_status": exec_result.plan_status.value,
                        "plan_steps": exec_result.steps_total,
                        "steps_completed": exec_result.steps_completed,
                        "steps_failed": exec_result.steps_failed,
                        "tool_calls": exec_result.metrics.tool_calls,
                        "plan_observations": serialized_obs
                    }

                    agent_response = AgentResponse(
                        response_id=generate_response_id(),
                        text=exec_result.final_response,
                        tool_calls=[],
                        success=exec_result.success,
                        metadata=metadata
                    )
            else:
                logger.info(f"Routing to DIRECT path: confidence={decision.confidence:.2f}")
                if plan.use_tools or plan.use_memory:
                    raise NotImplementedError("Tool and Memory execution paths are not yet supported directly.")

                # Execute via existing AgentRunner or Executor
                if plan.use_llm and self._runner is not None:
                    logger.info("Executing via AgentRunner action loop...")
                    run_result = self._runner.run(request, formatted_messages, memory_context=memory_context)
                    
                    # Merge the memory retrieval diagnostics into execution metrics
                    from dataclasses import replace, asdict
                    exec_metrics = replace(
                        run_result.execution_metrics,
                        memory_matches=memory_matches_ids,
                        memory_retrieval_duration_ms=memory_duration_ms
                    )
                    
                    response_metadata = {
                        "execution_mode": "direct",
                        "execution_metrics": asdict(exec_metrics)
                    }
                    if run_result.confirmation_required:
                        response_metadata["confirmation_required"] = True
                        response_metadata["pending_action_id"] = run_result.pending_action_id
                        response_metadata["tool_name"] = run_result.requested_tools[0] if run_result.requested_tools else ""
                        response_metadata["reason"] = run_result.text
                        if getattr(run_result, "tool_calls_data", None):
                            response_metadata["tool_calls"] = run_result.tool_calls_data

                    agent_response = AgentResponse(
                        response_id=generate_response_id(),
                        text=run_result.text,
                        tool_calls=[],
                        success=not run_result.confirmation_required,
                        metadata=response_metadata
                    )
                else:
                    logger.info("Executing via Executor...")
                    # Fallback to direct executor
                    raw_response = self._executor.execute(plan, formatted_messages)
                    agent_response = self._parser.parse_response(raw_response)
                    
                    # Merge metadata
                    new_metadata = dict(agent_response.metadata)
                    new_metadata["execution_mode"] = "direct"
                    agent_response = AgentResponse(
                        response_id=agent_response.response_id,
                        text=agent_response.text,
                        tool_calls=agent_response.tool_calls,
                        success=agent_response.success,
                        metadata=new_metadata
                    )

            # Create and store assistant Message
            assistant_message = Message(
                id=generate_message_id(),
                role=MessageRole.ASSISTANT,
                content=agent_response.text,
                timestamp=datetime.now(timezone.utc),
                metadata=sanitize_for_json(agent_response.metadata),
            )
            if self.conversation_manager and self.active_session_id:
                self.conversation_manager.add_message(self.active_session_id, assistant_message)
            self.conversation.add_message(assistant_message)
            logger.info("Assistant response stored.")

            # Memory writing scheduled asynchronously in the background
            if self._coordinator is not None:
                try:
                    scheduled = self._coordinator.submit(request.text)
                    if scheduled:
                        logger.info("Memory extraction task scheduled asynchronously in the background.")
                    else:
                        logger.debug("Memory extraction task was not scheduled (empty input, queue full, or coordinator shut down).")
                except Exception as e:
                    logger.error(f"Failed to schedule memory extraction task (isolated): {e}")

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

    def process_request_stream(self, request: AgentRequest, approval_action_id: str | None = None) -> Iterator[str]:
        """Processes an incoming request as a stream of text chunks.

        Args:
            request: The input AgentRequest object.
            approval_action_id: Optional approval action ID.

        Returns:
            Iterator[str]: An iterator yielding text chunks.

        Raises:
            Exception: If execution fails before or during streaming.
        """
        start_time = time.perf_counter()
        logger.info(f"Streaming request received: ID={request.request_id} (approval_id={approval_action_id})")

        try:
            # Check approval resumption
            if approval_action_id is not None and self._approval_manager is not None:
                action = self._approval_manager.get(approval_action_id)
                if not action:
                    yield "Error: Approved action not found."
                    return

                if action.status == PendingActionStatus.REJECTED:
                    self._active_plan = None
                    self._active_observations = None
                    
                    full_text = "Action was rejected by the user. Execution cancelled."
                    yield full_text
                    
                    agent_response = AgentResponse(
                        response_id=generate_response_id(),
                        text=full_text,
                        success=False,
                        metadata={"confirmation_required": False}
                    )
                    assistant_message = Message(
                        id=generate_message_id(),
                        role=MessageRole.ASSISTANT,
                        content=full_text,
                        timestamp=datetime.now(timezone.utc),
                        metadata=sanitize_for_json(agent_response.metadata),
                    )
                    if self.conversation_manager and self.active_session_id:
                        self.conversation_manager.add_message(self.active_session_id, assistant_message)
                    self.conversation.add_message(assistant_message)
                    return

                if action.status == PendingActionStatus.APPROVED:
                    if self._active_plan is not None:
                        logger.info("Resuming plan execution (streaming) after approval...")
                        exec_result = self._task_executor.execute(
                            plan=self._active_plan,
                            original_request_text=request.text,
                            approval_action_id=approval_action_id,
                            previous_observations=self._active_observations
                        )
                        
                        from app.planning.models import PlanStatus
                        if exec_result.plan_status == PlanStatus.WAITING_APPROVAL:
                            self._active_observations = exec_result.observations
                            response_metadata = {
                                "execution_mode": "planned",
                                "plan_id": self._active_plan.plan_id,
                                "plan_status": exec_result.plan_status.value,
                                "steps_total": len(self._active_plan.steps),
                                "steps_completed": exec_result.steps_completed,
                                "steps_failed": exec_result.steps_failed,
                                "confirmation_required": True,
                                "pending_action_id": exec_result.metadata.get("pending_action_id"),
                                "tool_name": exec_result.metadata.get("tool_name"),
                                "reason": exec_result.metadata.get("reason")
                            }
                        else:
                            self._active_plan = None
                            self._active_observations = None
                            response_metadata = {
                                "execution_mode": "planned",
                                "plan_id": exec_result.plan_id,
                                "plan_status": exec_result.plan_status.value,
                                "steps_total": exec_result.steps_total,
                                "steps_completed": exec_result.steps_completed,
                                "steps_failed": exec_result.steps_failed,
                                "plan_metrics": exec_result.metrics
                            }
                        yield exec_result.final_response
                        
                        # Store message
                        assistant_message = Message(
                            id=generate_message_id(),
                            role=MessageRole.ASSISTANT,
                            content=exec_result.final_response,
                            timestamp=datetime.now(timezone.utc),
                            metadata=sanitize_for_json(response_metadata),
                        )
                        if self.conversation_manager and self.active_session_id:
                            self.conversation_manager.add_message(self.active_session_id, assistant_message)
                        self.conversation.add_message(assistant_message)
                        return
                    
                    else:
                        # Direct approved stream execution
                        logger.info("Executing approved direct action (streaming)...")
                        from app.agent.models import ToolCall
                        tool_call = ToolCall(tool_name=action.tool_name, arguments=action.arguments)
                        tool_exec = getattr(self._runner, "_executor")
                        tool_result = tool_exec.execute(tool_call, approval_action_id=approval_action_id)
                        
                        import json
                        tool_content = json.dumps(tool_result.output) if tool_result.success else json.dumps({"error": tool_result.error})
                        tool_message = Message(
                            id=generate_message_id(),
                            role=MessageRole.TOOL,
                            content=tool_content,
                            timestamp=datetime.now(timezone.utc),
                            metadata={"tool_name": action.tool_name}
                        )
                        if self.conversation_manager and self.active_session_id:
                            self.conversation_manager.add_message(self.active_session_id, tool_message)
                        self.conversation.add_message(tool_message)
                        
                        # Format history without adding a duplicate user message
                        plan = self._planner.create_plan(request)
                        history = self.conversation.get_history()
                        if self.context_policy:
                            history = self.context_policy.select_history(history)
                        formatted_messages = self._formatter.format_history(history)
                        
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
                            except Exception as me:
                                logger.error(f"Memory retrieval failed: {me}")
                                raise

                        accumulator = []
                        response_metadata = {}
                        exec_metrics = None
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
                                response_metadata = {
                                    "execution_mode": "direct",
                                    "execution_metrics": exec_metrics
                                }
                                if exec_metrics.confirmation_required:
                                    response_metadata["confirmation_required"] = True
                                    response_metadata["pending_action_id"] = exec_metrics.pending_action_id
                                    response_metadata["tool_name"] = exec_metrics.requested_tools[0] if exec_metrics.requested_tools else ""
                                    if getattr(exec_metrics, "tool_calls_data", None):
                                        response_metadata["tool_calls"] = exec_metrics.tool_calls_data
                                break
                        
                        full_response_text = "".join(accumulator)
                        assistant_message = Message(
                            id=generate_message_id(),
                            role=MessageRole.ASSISTANT,
                            content=full_response_text,
                            timestamp=datetime.now(timezone.utc),
                            metadata=sanitize_for_json(response_metadata),
                        )
                        if self.conversation_manager and self.active_session_id:
                            self.conversation_manager.add_message(self.active_session_id, assistant_message)
                        self.conversation.add_message(assistant_message)
                        return

            # Standard streaming path (non-resumption)
            plan, formatted_messages = self._prepare_request(request)

            # Heuristic Routing decision
            decision = self._router.route(request)

            # Memory retrieval logic (runs for both direct and planned paths)
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
                except Exception as me:
                    logger.error(f"Memory retrieval failed: {me}")
                    raise

            accumulator = []
            exec_metrics = None
            response_metadata = {}
            is_planned = settings.planning_enabled and decision.mode == ExecutionMode.PLANNED

            if is_planned:
                logger.info(f"Routing to PLANNED path (stream): confidence={decision.confidence:.2f}")

                available_tools = []
                if self._runner is not None:
                    reg = getattr(self._runner, "_registry", None)
                    if reg is not None:
                        available_tools = reg.get_schemas()

                # Exclude the current user message (last message) from the planner context
                history_for_planner = formatted_messages[:-1] if formatted_messages else []

                # Formulate Plan
                task_plan = self._task_planner.create_plan(
                    request=request,
                    available_tools=available_tools,
                    conversation_history=history_for_planner,
                    memory_context=memory_context
                )

                # Execute Plan step-by-step
                exec_result = self._task_executor.execute(
                    plan=task_plan,
                    original_request_text=request.text,
                    routing_confidence=decision.confidence
                )

                from app.planning.models import PlanStatus
                if exec_result.plan_status == PlanStatus.WAITING_APPROVAL:
                    self._active_plan = task_plan
                    self._active_observations = exec_result.observations
                    response_metadata = {
                        "execution_mode": "planned",
                        "plan_id": task_plan.plan_id,
                        "plan_goal": task_plan.goal,
                        "plan_status": task_plan.status.value,
                        "steps_total": len(task_plan.steps),
                        "steps_completed": exec_result.steps_completed,
                        "steps_failed": exec_result.steps_failed,
                        "confirmation_required": True,
                        "pending_action_id": exec_result.metadata.get("pending_action_id"),
                        "tool_name": exec_result.metadata.get("tool_name"),
                        "reason": exec_result.metadata.get("reason")
                    }
                else:
                    response_metadata = {
                        "execution_mode": "planned",
                        "plan_id": task_plan.plan_id,
                        "plan_goal": task_plan.goal,
                        "plan_status": task_plan.status.value,
                        "steps_total": len(task_plan.steps),
                        "steps_completed": exec_result.steps_completed,
                        "steps_failed": exec_result.steps_failed,
                        "plan_metrics": exec_result.metrics
                    }
                final_text = exec_result.final_response
                accumulator.append(final_text)
                yield final_text
            else:
                logger.info(f"Routing to DIRECT path (stream): confidence={decision.confidence:.2f}")
                if plan.use_tools or plan.use_memory:
                    raise NotImplementedError("Tool and Memory execution paths are not yet supported for streaming.")

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
                            response_metadata = {
                                "execution_mode": "direct",
                                "execution_metrics": exec_metrics
                            }
                            if exec_metrics.confirmation_required:
                                response_metadata["confirmation_required"] = True
                                response_metadata["pending_action_id"] = exec_metrics.pending_action_id
                                response_metadata["tool_name"] = exec_metrics.requested_tools[0] if exec_metrics.requested_tools else ""
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
                metadata=sanitize_for_json(response_metadata),
            )
            if self.conversation_manager and self.active_session_id:
                self.conversation_manager.add_message(self.active_session_id, assistant_message)
            self.conversation.add_message(assistant_message)
            logger.info("Assistant response stored.")

            # Memory writing scheduled asynchronously in the background after successful response storage
            if self._coordinator is not None:
                try:
                    scheduled = self._coordinator.submit(request.text)
                    if scheduled:
                        logger.info("Memory extraction task scheduled asynchronously in the background.")
                    else:
                        logger.debug("Memory extraction task was not scheduled (empty input, queue full, or coordinator shut down).")
                except Exception as e:
                    logger.error(f"Failed to schedule memory extraction task (isolated): {e}")

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
        if self.conversation_manager and self.active_session_id:
            self.conversation_manager.add_message(self.active_session_id, user_message)
        self.conversation.add_message(user_message)
        logger.info("Conversation updated with user message.")

        # Formulate Plan using Planner
        logger.info("Formulating execution plan...")
        plan = self._planner.create_plan(request)
        logger.info(f"Intent classified: {plan.intent.intent_type.name} (confidence={plan.intent.confidence})")
        logger.info(f"Execution Plan: use_llm={plan.use_llm}, use_tools={plan.use_tools}, use_memory={plan.use_memory}")

        # Use MessageFormatter to get payload ready
        logger.info("Formatting started.")
        history = self.conversation.get_history()
        if self.context_policy:
            history = self.context_policy.select_history(history)
        formatted_messages = self._formatter.format_history(history)
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
