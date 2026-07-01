"""Conversation model storing ordered messages in-memory."""

from typing import List
from app.agent.messages import Message


class Conversation:
    """Maintains an ordered history of messages in the current session."""

    def __init__(self, max_history: int | None = None) -> None:
        """Initializes a new Conversation context.

        Args:
            max_history: Maximum number of messages to keep in history.
                         Oldest messages are dropped when reached.
        """
        self._messages: List[Message] = []
        self._max_history: int | None = max_history

    def add_message(self, message: Message) -> None:
        """Appends a new message to the conversation log.

        Args:
            message: The Message instance to add.
        """
        self._messages.append(message)
        self._enforce_limit()

    def remove_message(self, message_id: str) -> bool:
        """Removes a message from the log by its unique identifier.

        Args:
            message_id: The ID of the message to remove.

        Returns:
            bool: True if the message was found and removed, False otherwise.
        """
        initial_len = len(self._messages)
        self._messages = [m for m in self._messages if m.id != message_id]
        return len(self._messages) < initial_len

    def clear(self) -> None:
        """Removes all messages from the conversation history."""
        self._messages.clear()

    def get_history(self) -> List[Message]:
        """Returns the ordered list of messages in history.

        Returns:
            List[Message]: The list of all stored messages.
        """
        return list(self._messages)

    def _enforce_limit(self) -> None:
        """Trims message history if it exceeds the maximum size constraint."""
        if self._max_history is not None and len(self._messages) > self._max_history:
            self._messages = self._messages[-self._max_history:]
