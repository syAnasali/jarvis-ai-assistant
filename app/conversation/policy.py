"""Context-window policy implementation for bounding conversation history."""

from typing import List
from app.agent.messages import Message
from app.config.settings import settings


class ContextWindowPolicy:
    """Selects a bounded subset of recent messages to fit the LLM context window."""

    def __init__(self, max_messages: int | None = None, max_characters: int | None = None) -> None:
        """Initializes ContextWindowPolicy.

        Args:
            max_messages: Maximum messages to select. Defaults to settings.
            max_characters: Maximum total characters of content to select. Defaults to settings.
        """
        self._max_messages = max_messages if max_messages is not None else settings.conversation_context_max_messages
        self._max_characters = max_characters if max_characters is not None else settings.conversation_context_max_characters

    def select_history(self, messages: List[Message]) -> List[Message]:
        """Selects the most recent messages fitting the message count and character budget constraints.

        Always preserves the latest message intact. Returns messages in chronological order.

        Args:
            messages: Full list of messages in the conversation.

        Returns:
            List[Message]: The bounded history.
        """
        if not messages:
            return []

        # Start from the end (newest)
        selected: List[Message] = []
        total_chars = 0
        latest_message = messages[-1]

        # Always include the latest message
        selected.append(latest_message)
        total_chars += len(latest_message.content)

        # Iterate backwards starting from the second-to-last message
        for msg in reversed(messages[:-1]):
            # Check message count limit
            if len(selected) >= self._max_messages:
                break

            # Check character limit
            if total_chars + len(msg.content) > self._max_characters:
                break

            selected.append(msg)
            total_chars += len(msg.content)

        # Restore chronological order
        return list(reversed(selected))
