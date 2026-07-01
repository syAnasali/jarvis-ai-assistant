"""Runtime context manager for managing active state and session metadata."""

from typing import Dict, Any
from app.agent.models import AgentRequest


class ContextManager:
    """Manages active topics, requests, and metadata for the current user session."""

    def __init__(self) -> None:
        """Initializes the ContextManager with clean states."""
        self.current_topic: str | None = None
        self.active_request: AgentRequest | None = None
        self.session_metadata: Dict[str, Any] = {}

    def set_topic(self, topic: str) -> None:
        """Updates the current dialogue topic.

        Args:
            topic: The name or category of the active topic.
        """
        self.current_topic = topic

    def set_active_request(self, request: AgentRequest) -> None:
        """Tracks the current active request undergoing execution.

        Args:
            request: The active AgentRequest instance.
        """
        self.active_request = request

    def update_metadata(self, key: str, value: Any) -> None:
        """Sets or updates a session metadata variable.

        Args:
            key: The metadata lookup key.
            value: The metadata value.
        """
        self.session_metadata[key] = value

    def reset(self) -> None:
        """Clears all session-specific topics, active request state, and metadata."""
        self.current_topic = None
        self.active_request = None
        self.session_metadata.clear()
