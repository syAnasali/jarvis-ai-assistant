"""Normalizer and parser for model response payloads."""

from typing import Any, List
from app.agent.models import AgentResponse, ToolCall
from app.utils.id_generator import generate_response_id


class ResponseParser:
    """Parses raw provider LLM outputs into standardized AgentResponse models."""

    def _unwrap(self, response: Any) -> Any:
        """Helper to unwrap GenerationResult to raw response if necessary."""
        from app.ai.models import GenerationResult
        if isinstance(response, GenerationResult):
            return response.raw_response
        return response

    def parse_response(self, raw_output: Any) -> AgentResponse:
        """Parses a raw output into the unified AgentResponse format.

        Args:
            raw_output: The raw provider-specific completion output (dictionary or SDK object).

        Returns:
            AgentResponse: Unified parsed response instance.
        """
        unwrapped = self._unwrap(raw_output)
        content = self._extract_content(unwrapped)
        if not content:
            content = str(unwrapped)

        response_id = generate_response_id()

        return AgentResponse(
            response_id=response_id,
            text=content.strip(),
            tool_calls=[],
            success=True,
            metadata={}
        )

    def parse_stream_chunk(self, raw_chunk: Any) -> str:
        """Parses a single raw provider chunk to extract text content.

        Args:
            raw_chunk: A single streaming response chunk (dictionary or SDK object).

        Returns:
            str: The extracted text content chunk, or an empty string.
        """
        if isinstance(raw_chunk, dict):
            msg = raw_chunk.get("message", {})
            if isinstance(msg, dict):
                return msg.get("content", "")
            return getattr(msg, "content", "") or ""

        msg = getattr(raw_chunk, "message", None)
        if msg is not None:
            return getattr(msg, "content", "") or ""

        return ""

    def has_tool_calls(self, raw_output: Any) -> bool:
        """Checks if a provider response contains tool execution requests.

        Args:
            raw_output: The raw provider response output.

        Returns:
            bool: True if tool calls exist, False otherwise.
        """
        unwrapped = self._unwrap(raw_output)
        if isinstance(unwrapped, dict):
            msg = unwrapped.get("message", {})
            if isinstance(msg, dict):
                return bool(msg.get("tool_calls"))
            return bool(getattr(msg, "tool_calls", None))
        
        msg = getattr(unwrapped, "message", None)
        if msg is not None:
            return bool(getattr(msg, "tool_calls", None))
        
        return False

    def parse_tool_calls(self, raw_output: Any) -> List[ToolCall]:
        """Parses raw model output into a list of unified ToolCall models.

        Args:
            raw_output: The raw provider response output.

        Returns:
            List[ToolCall]: A list of ToolCall instances.
        """
        unwrapped = self._unwrap(raw_output)
        raw_calls = []
        if isinstance(unwrapped, dict):
            msg = unwrapped.get("message", {})
            if isinstance(msg, dict):
                raw_calls = msg.get("tool_calls") or []
            else:
                raw_calls = getattr(msg, "tool_calls", None) or []
        else:
            msg = getattr(unwrapped, "message", None)
            if msg is not None:
                raw_calls = getattr(msg, "tool_calls", None) or []

        parsed_calls = []
        for call in raw_calls:
            try:
                if isinstance(call, dict):
                    func = call.get("function", {})
                    if isinstance(func, dict):
                        name = func.get("name")
                        args = func.get("arguments")
                    else:
                        name = getattr(func, "name", None)
                        args = getattr(func, "arguments", None)
                else:
                    func = getattr(call, "function", None)
                    if func is not None:
                        name = getattr(func, "name", None)
                        args = getattr(func, "arguments", None)
                    else:
                        name = None
                        args = None

                if not name:
                    continue

                if args is None:
                    norm_args = {}
                elif isinstance(args, dict):
                    norm_args = dict(args)
                else:
                    norm_args = {}

                parsed_calls.append(ToolCall(tool_name=name, arguments=norm_args))
            except Exception:
                continue

        return parsed_calls

    def _extract_content(self, raw_output: Any) -> str:
        """Extracts the message content string from raw provider outputs.

        Args:
            raw_output: The raw provider output.

        Returns:
            str: Extracted text content.
        """
        if isinstance(raw_output, dict):
            return self._extract_from_dict(raw_output)
        return self._extract_from_object(raw_output)

    def _extract_from_dict(self, raw_dict: dict) -> str:
        """Extracts content from a dictionary response payload."""
        msg = raw_dict.get("message", {})
        if isinstance(msg, dict):
            return msg.get("content", "")
        return getattr(msg, "content", "")

    def _extract_from_object(self, raw_obj: Any) -> str:
        """Extracts content from an SDK object response payload."""
        msg = getattr(raw_obj, "message", None)
        if msg is not None:
            return getattr(msg, "content", "") or ""
        return str(raw_obj)
