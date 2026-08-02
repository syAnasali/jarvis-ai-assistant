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

    def select_history_with_diagnostics(self, messages: List[Message]) -> tuple[List[Message], int, int]:
        """Selects recent messages and calculates used vs skipped message counts.

        Args:
            messages: Full list of messages in the conversation.

        Returns:
            tuple[List[Message], int, int]: (selected_messages, messages_used, messages_skipped)
        """
        if not messages:
            return [], 0, 0

        total_input_count = len(messages)
        # Filter out empty or irrelevant turns from older history
        cleaned_messages = []
        for i, msg in enumerate(messages):
            # Always keep latest 4 messages regardless
            is_recent = i >= total_input_count - 4
            if is_recent or (msg.content and msg.content.strip()):
                cleaned_messages.append(msg)

        selected: List[Message] = []
        total_chars = 0
        latest_message = cleaned_messages[-1]

        # Always include the latest message
        selected.append(latest_message)
        total_chars += len(latest_message.content)

        # Iterate backwards starting from the second-to-last message
        for msg in reversed(cleaned_messages[:-1]):
            # Check message count limit
            if len(selected) >= self._max_messages:
                break

            # Check character limit
            if total_chars + len(msg.content) > self._max_characters:
                break

            selected.append(msg)
            total_chars += len(msg.content)

        # Restore chronological order
        result_messages = list(reversed(selected))
        used_count = len(result_messages)
        skipped_count = max(0, total_input_count - used_count)
        return result_messages, used_count, skipped_count

    def select_history(self, messages: List[Message]) -> List[Message]:
        """Selects the most recent messages fitting the message count and character budget constraints.

        Always preserves the latest message intact. Returns messages in chronological order.

        Args:
            messages: Full list of messages in the conversation.

        Returns:
            List[Message]: The bounded history.
        """
        selected, _, _ = self.select_history_with_diagnostics(messages)
        return selected
