"""Formatter to standardize internal messages for provider APIs."""

from typing import Dict, List, Any
from app.agent.messages import Message


class MessageFormatter:
    """Translates internal Message dataclasses into provider message formats."""

    def to_provider_message(self, message: Message) -> Dict[str, Any]:
        """Translates a single internal Message into a standard dictionary context.

        Args:
            message: The internal Message instance.

        Returns:
            Dict[str, Any]: Standard formatted dictionary message.
        """
        payload: Dict[str, Any] = {
            "role": message.role.value,
            "content": message.content,
        }

        # Adapt tool-specific turns
        if message.role.value == "tool":
            payload["name"] = message.metadata.get("tool_name", "")
        elif message.role.value == "assistant":
            tool_calls = message.metadata.get("tool_calls")
            if tool_calls:
                payload["tool_calls"] = tool_calls

        return payload

    def format_history(self, history: List[Message]) -> List[Dict[str, Any]]:
        """Translates a list of messages into a provider payload format.

        Args:
            history: List of internal messages.

        Returns:
            List[Dict[str, Any]]: List of standard formatted message dicts.
        """
        return [self.to_provider_message(msg) for msg in history]
