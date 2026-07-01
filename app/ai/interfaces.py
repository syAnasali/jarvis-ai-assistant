"""Interfaces for AI model provider abstractions."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseLLMProvider(ABC):
    """Abstract base class representing an LLM backend provider."""

    @abstractmethod
    def initialize(self) -> None:
        """Initializes client connections or local models.

        Raises:
            Exception: If initialization fails.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully disconnects or shuts down local models."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the provider is currently online and ready.

        Returns:
            bool: True if available, False otherwise.
        """
        pass

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None
    ) -> Any:
        """Sends messages to the LLM and retrieves the raw provider response.

        Args:
            messages: List of structured message dictionaries.
            options: Optional runtime configuration options.

        Returns:
            Any: Raw provider output.

        Raises:
            Exception: If the request fails.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Performs a diagnostic check of provider readiness.

        Returns:
            Dict[str, Any]: Health status details.
        """
        pass
