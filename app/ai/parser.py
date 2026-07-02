"""Normalizer and parser for model response payloads."""

from typing import Any
from app.agent.models import AgentResponse
from app.utils.id_generator import generate_response_id


class ResponseParser:
    """Parses raw provider LLM outputs into standardized AgentResponse models."""

    def parse_response(self, raw_output: Any) -> AgentResponse:
        """Parses a raw output into the unified AgentResponse format.

        Args:
            raw_output: The raw provider-specific completion output (dictionary or SDK object).

        Returns:
            AgentResponse: Unified parsed response instance.
        """
        content = self._extract_content(raw_output)
        if not content:
            content = str(raw_output)

        response_id = generate_response_id()

        return AgentResponse(
            response_id=response_id,
            text=content.strip(),
            tool_calls=[],
            success=True,
            metadata={}
        )

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
