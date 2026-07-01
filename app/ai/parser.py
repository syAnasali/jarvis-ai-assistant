"""Normalizer and parser for model response payloads."""

from typing import Any
from app.agent.models import AgentResponse


class ResponseParser:
    """Parses raw provider LLM outputs into standardized AgentResponse models."""

    def parse_response(self, raw_output: Any) -> AgentResponse:
        """Parses a raw output into the unified AgentResponse format.

        This functions as an extension point for provider-specific subclasses
        to override and parse their specific payload shapes.

        Args:
            raw_output: The raw provider-specific completion output.

        Returns:
            AgentResponse: Unified parsed response instance.

        Raises:
            NotImplementedError: Must be subclassed for parsing details.
        """
        raise NotImplementedError("Subclasses must implement parse_response for specific providers.")
