"""Agent runner that orchestrates the model-driven tool execution loop."""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import List, Dict, Any
from app.core.exceptions import LLMError
from app.core.constants import MAX_AGENT_ITERATIONS
from app.ai.manager import LLMManager
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.ai.parser import ResponseParser
from app.agent.models import AgentRequest, AgentResponse, ToolCall
from app.agent.metrics import AgentIterationMetrics, AgentExecutionMetrics
from app.ai.models import GenerationMetrics, GenerationResult, GenerationProfile
from app.ai.scheduler import InferencePriority
from app.ai.prompts import PromptManager
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("agent_runner")


@dataclass(frozen=True)
class AgentRunResult:
    """Wrapped result containing the final text response and execution metrics."""

    text: str
    execution_metrics: AgentExecutionMetrics
    requested_tools: tuple[str, ...] = ()
    pending_action_id: str | None = None
    confirmation_required: bool = False


class AgentRunner:
    """Orchestrates native model-driven tool calling action loops."""

    def __init__(
        self,
        llm_manager: LLMManager,
        registry: ToolRegistry,
        executor: ToolExecutor,
        parser: ResponseParser,
        prompt_manager: PromptManager | None = None
    ) -> None:
        """Initializes the AgentRunner.

        Args:
            llm_manager: Manager to route calls to the active provider.
            registry: Registry containing discovered system tools.
            executor: Safe execution barrier for tools.
            parser: Parser to evaluate and normalize provider responses.
            prompt_manager: Prompt manager to retrieve tool prompts/policies.
        """
        self._llm_manager = llm_manager
        self._registry = registry
        self._executor = executor
        self._parser = parser
        self._prompt_manager = prompt_manager or PromptManager()

    def run(self, request: AgentRequest, formatted_history: List[Dict[str, Any]], memory_context: str = "") -> AgentRunResult:
        """Runs the bounded action loop synchronously until a final response is generated.

        Args:
            request: The active AgentRequest.
            formatted_history: Already formatted conversation messages.
            memory_context: Prebuilt memory context string.

        Returns:
            AgentRunResult: The final text response and aggregate execution metrics.

        Raises:
            LLMError: If the iteration limit is reached.
        """
        start_time = time.perf_counter()
        model_calls = 0
        tool_calls_count = 0
        all_requested_tools = []
        iteration_metrics_list: List[AgentIterationMetrics] = []

        schemas = self._registry.get_schemas()

        # Setup working messages following the preferred system-context order
        working_messages = []
        working_messages.append({"role": "system", "content": self._prompt_manager.system_prompt()})
        if schemas:
            working_messages.append({"role": "system", "content": self._prompt_manager.tool_use_policy()})
        if memory_context:
            working_messages.append({"role": "system", "content": memory_context})
        working_messages.extend(formatted_history)

        for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
            iter_start_time = time.perf_counter()
            logger.info(f"Agent iteration {iteration} of {MAX_AGENT_ITERATIONS} started.")
            logger.info(f"Supplying {len(schemas)} tool schemas to the model.")

            # Decide profile: TOOL_SELECTION for first turn (no tools called yet), FAST for follow-ups
            current_profile = GenerationProfile.TOOL_SELECTION if tool_calls_count == 0 else GenerationProfile.FAST

            gen_result = self._llm_manager.generate(
                working_messages,
                tools=schemas,
                profile=current_profile,
                priority=InferencePriority.FOREGROUND
            )
            model_calls += 1
            metrics = gen_result.metrics

            # Parse tool calls
            raw_response = gen_result.raw_response
            has_calls = self._parser.has_tool_calls(raw_response)
            parsed_calls = self._parser.parse_tool_calls(raw_response) if has_calls else []

            iter_duration_ms = (time.perf_counter() - iter_start_time) * 1000

            logger.info(
                f"Agent iteration completed: "
                f"iteration={iteration}, "
                f"duration_ms={iter_duration_ms:.2f}, "
                f"provider={metrics.provider}, "
                f"model={metrics.model}, "
                f"load_duration_ms={metrics.load_duration_ms}, "
                f"prompt_eval_duration_ms={metrics.prompt_eval_duration_ms}, "
                f"generation_duration_ms={metrics.generation_duration_ms}, "
                f"prompt_tokens={metrics.prompt_tokens}, "
                f"generated_tokens={metrics.generated_tokens}, "
                f"tokens_per_second={metrics.tokens_per_second}, "
                f"tool_calls={len(parsed_calls)}, "
                f"profile={metrics.generation_profile}"
            )

            if has_calls:
                for tc in parsed_calls:
                    if tc.tool_name not in all_requested_tools:
                        all_requested_tools.append(tc.tool_name)

            if not has_calls:
                logger.info("Final model response produced.")
                
                # Record iteration metrics
                iter_metric = AgentIterationMetrics(
                    iteration=iteration,
                    duration_ms=iter_duration_ms,
                    model_metrics=metrics,
                    tool_calls_count=0
                )
                iteration_metrics_list.append(iter_metric)

                total_duration_ms = (time.perf_counter() - start_time) * 1000
                exec_metrics = AgentExecutionMetrics(
                    total_duration_ms=total_duration_ms,
                    iterations=iteration,
                    model_calls=model_calls,
                    tool_calls=tool_calls_count,
                    iteration_metrics=iteration_metrics_list,
                    requested_tools=tuple(all_requested_tools)
                )

                agent_response = self._parser.parse_response(raw_response)
                return AgentRunResult(
                    text=agent_response.text, 
                    execution_metrics=exec_metrics,
                    requested_tools=tuple(all_requested_tools)
                )

            logger.info(f"Model requested tool execution for {len(parsed_calls)} tools.")
            tool_calls_count += len(parsed_calls)

            # Construct and append assistant turn
            assistant_turn = self._format_assistant_turn(raw_response, parsed_calls)
            working_messages.append(assistant_turn)

            # Execute tool calls
            for tc in parsed_calls:
                logger.info(f"Requested tool name: '{tc.tool_name}'")
                tool_result = self._executor.execute(tc)
                
                # Intercept confirmation required
                if tool_result.metadata.get("confirmation_required"):
                    logger.warning(f"Agent execution suspended: confirmation required for tool '{tc.tool_name}'")
                    iter_metric = AgentIterationMetrics(
                        iteration=iteration,
                        duration_ms=(time.perf_counter() - iter_start_time) * 1000,
                        model_metrics=metrics,
                        tool_calls_count=len(parsed_calls)
                    )
                    iteration_metrics_list.append(iter_metric)
                    
                    total_duration_ms = (time.perf_counter() - start_time) * 1000
                    exec_metrics = AgentExecutionMetrics(
                        total_duration_ms=total_duration_ms,
                        iterations=iteration,
                        model_calls=model_calls,
                        tool_calls=tool_calls_count,
                        iteration_metrics=iteration_metrics_list,
                        requested_tools=tuple(all_requested_tools),
                        pending_action_id=tool_result.metadata.get("pending_action_id"),
                        confirmation_required=True
                    )
                    return AgentRunResult(
                        text=tool_result.error or f"Execution of tool '{tc.tool_name}' requires your confirmation.",
                        execution_metrics=exec_metrics,
                        requested_tools=tuple(all_requested_tools),
                        pending_action_id=tool_result.metadata.get("pending_action_id"),
                        confirmation_required=True
                    )

                # Format tool result turn
                tool_turn = self._format_tool_turn(tc, tool_result)
                working_messages.append(tool_turn)
                logger.info(f"Tool result returned to model: tool={tc.tool_name} success={tool_result.success}")

            # Record iteration metrics
            iter_metric = AgentIterationMetrics(
                iteration=iteration,
                duration_ms=iter_duration_ms,
                model_metrics=metrics,
                tool_calls_count=len(parsed_calls)
            )
            iteration_metrics_list.append(iter_metric)

        logger.error("Agent iteration limit reached.")
        raise LLMError(f"Agent reached the maximum iteration limit of {MAX_AGENT_ITERATIONS} turns.")

    def run_stream(self, request: AgentRequest, formatted_history: List[Dict[str, Any]], memory_context: str = "") -> Iterator[str]:
        """Runs the bounded action loop, executing intermediate tool turns, and streaming the final text.

        Args:
            request: The active AgentRequest.
            formatted_history: Already formatted conversation messages.
            memory_context: Prebuilt memory context string.

        Returns:
            Iterator[str]: Iterator yielding final text response fragments.

        Raises:
            LLMError: If the iteration limit is reached.
        """
        start_time = time.perf_counter()
        model_calls = 0
        tool_calls_count = 0
        all_requested_tools = []
        iteration_metrics_list: List[AgentIterationMetrics] = []

        schemas = self._registry.get_schemas()

        # Setup working messages following the preferred system-context order
        working_messages = []
        working_messages.append({"role": "system", "content": self._prompt_manager.system_prompt()})
        if schemas:
            working_messages.append({"role": "system", "content": self._prompt_manager.tool_use_policy()})
        if memory_context:
            working_messages.append({"role": "system", "content": memory_context})
        working_messages.extend(formatted_history)

        for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
            iter_start_time = time.perf_counter()
            logger.info(f"Agent streaming iteration {iteration} of {MAX_AGENT_ITERATIONS} started.")
            logger.info(f"Supplying {len(schemas)} tool schemas to the model.")

            # Decide profile: TOOL_SELECTION for first turn (no tools called yet), FAST for follow-ups
            current_profile = GenerationProfile.TOOL_SELECTION if tool_calls_count == 0 else GenerationProfile.FAST

            stream = self._llm_manager.generate_stream(working_messages, tools=schemas, profile=current_profile)
            model_calls += 1

            text_accumulator: List[str] = []
            tool_calls_accumulator: List[ToolCall] = []
            first_chunk = True
            raw_response_for_structure: Any = None
            last_chunk: Any = None

            for raw_chunk in stream:
                last_chunk = raw_chunk
                if first_chunk:
                    logger.info("First streaming chunk received.")
                    first_chunk = False
                    raw_response_for_structure = raw_chunk

                if self._parser.has_tool_calls(raw_chunk):
                    tc_list = self._parser.parse_tool_calls(raw_chunk)
                    for tc in tc_list:
                        if tc not in tool_calls_accumulator:
                            tool_calls_accumulator.append(tc)
                else:
                    text_chunk = self._parser.parse_stream_chunk(raw_chunk)
                    if text_chunk:
                        text_accumulator.append(text_chunk)
                        # Yield text chunks only if we are in the final text response turn (no tool calls)
                        if not tool_calls_accumulator:
                            yield text_chunk

            iter_duration_ms = (time.perf_counter() - iter_start_time) * 1000

            # Try to extract metrics if last_chunk has them, else create empty metrics
            metrics = None
            if last_chunk is not None:
                def get_metric(obj: Any, key: str) -> Any:
                    if isinstance(obj, dict):
                        return obj.get(key)
                    return getattr(obj, key, None)

                def to_ms(ns: Any) -> float | None:
                    if ns is None:
                        return None
                    try:
                        return float(ns) / 1_000_000.0
                    except (ValueError, TypeError):
                        return None

                total_duration_ms = to_ms(get_metric(last_chunk, "total_duration"))
                load_duration_ms = to_ms(get_metric(last_chunk, "load_duration"))
                prompt_eval_duration_ms = to_ms(get_metric(last_chunk, "prompt_eval_duration"))
                generation_duration_ms = to_ms(get_metric(last_chunk, "eval_duration"))
                p_tokens = get_metric(last_chunk, "prompt_eval_count")
                g_tokens = get_metric(last_chunk, "eval_count")

                tokens_per_second = None
                eval_ns = get_metric(last_chunk, "eval_duration")
                if g_tokens is not None and eval_ns is not None:
                    try:
                        gen_sec = float(eval_ns) / 1_000_000_000.0
                        if gen_sec > 0:
                            tokens_per_second = float(g_tokens) / gen_sec
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass

                metrics = GenerationMetrics(
                    provider="ollama",
                    model=get_metric(last_chunk, "model") or "unknown",
                    total_duration_ms=total_duration_ms,
                    load_duration_ms=load_duration_ms,
                    prompt_eval_duration_ms=prompt_eval_duration_ms,
                    generation_duration_ms=generation_duration_ms,
                    prompt_tokens=p_tokens,
                    generated_tokens=g_tokens,
                    tokens_per_second=tokens_per_second,
                    generation_profile=current_profile.value,
                    metadata=last_chunk if isinstance(last_chunk, dict) else getattr(last_chunk, "__dict__", {})
                )

            logger.info(
                f"Agent iteration completed: "
                f"iteration={iteration}, "
                f"duration_ms={iter_duration_ms:.2f}, "
                f"provider={metrics.provider if metrics else 'ollama'}, "
                f"model={metrics.model if metrics else 'unknown'}, "
                f"load_duration_ms={metrics.load_duration_ms if metrics else None}, "
                f"prompt_eval_duration_ms={metrics.prompt_eval_duration_ms if metrics else None}, "
                f"generation_duration_ms={metrics.generation_duration_ms if metrics else None}, "
                f"prompt_tokens={metrics.prompt_tokens if metrics else None}, "
                f"generated_tokens={metrics.generated_tokens if metrics else None}, "
                f"tokens_per_second={metrics.tokens_per_second if metrics else None}, "
                f"tool_calls={len(tool_calls_accumulator)}, "
                f"profile={metrics.generation_profile if metrics else current_profile.value}"
            )

            if tool_calls_accumulator:
                for tc in tool_calls_accumulator:
                    if tc.tool_name not in all_requested_tools:
                        all_requested_tools.append(tc.tool_name)

            if tool_calls_accumulator:
                logger.info(f"Model requested tool execution for {len(tool_calls_accumulator)} tools.")
                tool_calls_count += len(tool_calls_accumulator)

                # Construct and append assistant turn
                assistant_turn = self._format_assistant_turn(raw_response_for_structure, tool_calls_accumulator, "".join(text_accumulator))
                working_messages.append(assistant_turn)

                # Execute tool calls
                for tc in tool_calls_accumulator:
                    logger.info(f"Requested tool name: '{tc.tool_name}'")
                    tool_result = self._executor.execute(tc)
                    
                    # Intercept confirmation required
                    if tool_result.metadata.get("confirmation_required"):
                        logger.warning(f"Agent streaming suspended: confirmation required for tool '{tc.tool_name}'")
                        iter_metric = AgentIterationMetrics(
                            iteration=iteration,
                            duration_ms=iter_duration_ms,
                            model_metrics=metrics,
                            tool_calls_count=len(tool_calls_accumulator)
                        )
                        iteration_metrics_list.append(iter_metric)
                        
                        total_duration_ms = (time.perf_counter() - start_time) * 1000
                        exec_metrics = AgentExecutionMetrics(
                            total_duration_ms=total_duration_ms,
                            iterations=iteration,
                            model_calls=model_calls,
                            tool_calls=tool_calls_count,
                            iteration_metrics=iteration_metrics_list,
                            requested_tools=tuple(all_requested_tools),
                            pending_action_id=tool_result.metadata.get("pending_action_id"),
                            confirmation_required=True
                        )
                        yield tool_result.error or f"Execution of tool '{tc.tool_name}' requires your confirmation."
                        return exec_metrics

                    # Format tool result turn
                    tool_turn = self._format_tool_turn(tc, tool_result)
                    working_messages.append(tool_turn)
                    logger.info(f"Tool result returned to model: tool={tc.tool_name} success={tool_result.success}")

                # Record iteration metrics
                iter_metric = AgentIterationMetrics(
                    iteration=iteration,
                    duration_ms=iter_duration_ms,
                    model_metrics=metrics,
                    tool_calls_count=len(tool_calls_accumulator)
                )
                iteration_metrics_list.append(iter_metric)

                # Continue iteration
                continue
            else:
                logger.info("Final model response produced.")
                
                # Record iteration metrics
                iter_metric = AgentIterationMetrics(
                    iteration=iteration,
                    duration_ms=iter_duration_ms,
                    model_metrics=metrics,
                    tool_calls_count=0
                )
                iteration_metrics_list.append(iter_metric)

                total_duration_ms = (time.perf_counter() - start_time) * 1000
                exec_metrics = AgentExecutionMetrics(
                    total_duration_ms=total_duration_ms,
                    iterations=iteration,
                    model_calls=model_calls,
                    tool_calls=tool_calls_count,
                    iteration_metrics=iteration_metrics_list,
                    requested_tools=tuple(all_requested_tools)
                )

                # Return the execution metrics to StopIteration value
                return exec_metrics

        logger.error("Agent iteration limit reached.")
        raise LLMError(f"Agent reached the maximum iteration limit of {MAX_AGENT_ITERATIONS} turns.")

    def _format_assistant_turn(
        self,
        raw_response: Any,
        tool_calls: List[ToolCall],
        accumulated_text: str = ""
    ) -> Dict[str, Any]:
        """Formats the assistant tool-request turn in a provider-neutral structure."""
        content = ""
        if accumulated_text:
            content = accumulated_text
        elif isinstance(raw_response, dict):
            content = raw_response.get("message", {}).get("content", "") or ""
        else:
            msg_obj = getattr(raw_response, "message", None)
            if msg_obj is not None:
                content = getattr(msg_obj, "content", "") or ""

        formatted_calls = []
        for tc in tool_calls:
            formatted_calls.append({
                "type": "function",
                "function": {
                    "name": tc.tool_name,
                    "arguments": tc.arguments
                }
            })

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": formatted_calls
        }

    def _format_tool_turn(self, tool_call: ToolCall, tool_result: Any) -> Dict[str, Any]:
        """Formats the tool result turn in a provider-neutral structure."""
        if tool_result.success:
            content_str = json.dumps(tool_result.output)
        else:
            content_str = json.dumps({"error": tool_result.error})

        return {
            "role": "tool",
            "name": tool_call.tool_name,
            "content": content_str
        }
