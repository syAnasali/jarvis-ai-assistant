"""Normalizer and parser for model response payloads."""

import uuid
from typing import Any
from app.agent.models import AgentResponse


class ResponseParser:
    """Parses raw provider LLM outputs into standardized AgentResponse models."""

    def parse_response(self, raw_output: Any) -> AgentResponse:
        """Parses a raw output into the unified AgentResponse format.

        Args:
            raw_output: The raw provider-specific completion output (dictionary or SDK object).

        Returns:
            AgentResponse: Unified parsed response instance.
        """
        content = ""
        # Check dictionary-like response structure
        if isinstance(raw_output, dict):
            msg = raw_output.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = getattr(msg, "content", "")
        else:
            # Check SDK-object response structure (e.g. ChatResponse)
            msg = getattr(raw_output, "message", None)
            if msg is not None:
                content = getattr(msg, "content", "")

        # Fallback if content was not resolved
        if not content:
            content = str(raw_output)

        response_id = f"resp_{uuid.uuid4().hex[:8]}"

        return AgentResponse(
            response_id=response_id,
            text=content.strip(),
            tool_calls=[],
            success=True,
            metadata={}
        )
