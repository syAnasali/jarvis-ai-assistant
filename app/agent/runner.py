"""Agent runner that orchestrates the model-driven tool execution loop."""

import json
import time
from collections.abc import Iterator
from typing import List, Dict, Any
from app.core.exceptions import LLMError
from app.core.constants import MAX_AGENT_ITERATIONS
from app.ai.manager import LLMManager
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.ai.parser import ResponseParser
from app.agent.models import AgentRequest, AgentResponse, ToolCall
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("agent_runner")


class AgentRunner:
    """Orchestrates native model-driven tool calling action loops."""

    def __init__(
        self,
        llm_manager: LLMManager,
        registry: ToolRegistry,
        executor: ToolExecutor,
        parser: ResponseParser
    ) -> None:
        """Initializes the AgentRunner.

        Args:
            llm_manager: Manager to route calls to the active provider.
            registry: Registry containing discovered system tools.
            executor: Safe execution barrier for tools.
            parser: Parser to evaluate and normalize provider responses.
        """
        self._llm_manager = llm_manager
        self._registry = registry
        self._executor = executor
        self._parser = parser

    def run(self, request: AgentRequest, formatted_history: List[Dict[str, Any]]) -> AgentResponse:
        """Runs the bounded action loop synchronously until a final response is generated.

        Args:
            request: The active AgentRequest.
            formatted_history: Already formatted conversation messages.

        Returns:
            AgentResponse: Standardized final agent response.

        Raises:
            LLMError: If the iteration limit is reached.
        """
        working_messages = list(formatted_history)
        schemas = self._registry.get_schemas()

        for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
            logger.info(f"Agent iteration {iteration} of {MAX_AGENT_ITERATIONS} started.")
            logger.info(f"Supplying {len(schemas)} tool schemas to the model.")

            raw_response = self._llm_manager.generate(working_messages, tools=schemas)

            if not self._parser.has_tool_calls(raw_response):
                logger.info("Final model response produced.")
                return self._parser.parse_response(raw_response)

            tool_calls = self._parser.parse_tool_calls(raw_response)
            logger.info(f"Model requested tool execution for {len(tool_calls)} tools.")

            # Construct and append assistant turn
            assistant_turn = self._format_assistant_turn(raw_response, tool_calls)
            working_messages.append(assistant_turn)

            # Execute tool calls
            for tc in tool_calls:
                logger.info(f"Requested tool name: '{tc.tool_name}'")
                tool_result = self._executor.execute(tc)
                
                # Format tool result turn
                tool_turn = self._format_tool_turn(tc, tool_result)
                working_messages.append(tool_turn)
                logger.info(f"Tool result returned to model: tool={tc.tool_name} success={tool_result.success}")

        logger.error("Agent iteration limit reached.")
        raise LLMError(f"Agent reached the maximum iteration limit of {MAX_AGENT_ITERATIONS} turns.")

    def run_stream(self, request: AgentRequest, formatted_history: List[Dict[str, Any]]) -> Iterator[str]:
        """Runs the bounded action loop, executing intermediate tool turns, and streaming the final text.

        Args:
            request: The active AgentRequest.
            formatted_history: Already formatted conversation messages.

        Returns:
            Iterator[str]: Iterator yielding final text response fragments.

        Raises:
            LLMError: If the iteration limit is reached.
        """
        working_messages = list(formatted_history)
        schemas = self._registry.get_schemas()

        for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
            logger.info(f"Agent streaming iteration {iteration} of {MAX_AGENT_ITERATIONS} started.")
            logger.info(f"Supplying {len(schemas)} tool schemas to the model.")

            stream = self._llm_manager.generate_stream(working_messages, tools=schemas)

            text_accumulator: List[str] = []
            tool_calls_accumulator: List[ToolCall] = []
            first_chunk = True
            raw_response_for_structure: Any = None

            for raw_chunk in stream:
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

            if tool_calls_accumulator:
                logger.info(f"Model requested tool execution for {len(tool_calls_accumulator)} tools.")

                # Construct and append assistant turn
                assistant_turn = self._format_assistant_turn(raw_response_for_structure, tool_calls_accumulator, "".join(text_accumulator))
                working_messages.append(assistant_turn)

                # Execute tool calls
                for tc in tool_calls_accumulator:
                    logger.info(f"Requested tool name: '{tc.tool_name}'")
                    tool_result = self._executor.execute(tc)
                    
                    # Format tool result turn
                    tool_turn = self._format_tool_turn(tc, tool_result)
                    working_messages.append(tool_turn)
                    logger.info(f"Tool result returned to model: tool={tc.tool_name} success={tool_result.success}")

                # Continue iteration
                continue
            else:
                logger.info("Final model response produced.")
                return

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
