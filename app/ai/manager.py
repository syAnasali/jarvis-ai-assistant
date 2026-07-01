"""Manager for registering and coordinating active LLM providers."""

from typing import Dict, Any
from app.ai.interfaces import BaseLLMProvider


class LLMManager:
    """Coordinates registration and switching of active AI LLM providers."""

    def __init__(self) -> None:
        """Initializes the LLMManager with empty provider registry."""
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._active_provider_name: str | None = None

    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """Registers an AI provider in the manager.

        Args:
            name: Unique registration name for the provider.
            provider: Concrete provider instance.
        """
        self._providers[name] = provider

    def switch_provider(self, name: str) -> None:
        """Switches the active provider to the registered provider.

        Args:
            name: Name of the registered provider.

        Raises:
            KeyError: If the provider is not registered.
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' is not registered.")
        self._active_provider_name = name

    def get_active_provider(self) -> BaseLLMProvider | None:
        """Retrieves the currently active provider instance.

        Returns:
            BaseLLMProvider | None: Active provider, or None if none selected.
        """
        if not self._active_provider_name:
            return None
        return self._providers[self._active_provider_name]

    def get_provider(self, name: str) -> BaseLLMProvider:
        """Retrieves a registered provider by name.

        Args:
            name: Registration name of the provider.

        Returns:
            BaseLLMProvider: The requested provider.

        Raises:
            KeyError: If the provider is not registered.
        """
        return self._providers[name]

    def health_check(self) -> Dict[str, Any]:
        """Aggregates health diagnostics for all registered providers.

        Returns:
            Dict[str, Any]: Registry health details.
        """
        status: Dict[str, Any] = {
            "active_provider": self._active_provider_name,
            "registered_providers": list(self._providers.keys()),
            "provider_statuses": {}
        }
        for name, provider in self._providers.items():
            try:
                status["provider_statuses"][name] = provider.health_check()
            except Exception as e:
                status["provider_statuses"][name] = {"status": "error", "message": str(e)}
        return status
