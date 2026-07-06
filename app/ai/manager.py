"""Manager for registering and coordinating active LLM providers."""

from collections.abc import Iterator
import threading
from typing import Dict, Any, List
from app.ai.interfaces import BaseLLMProvider
from app.ai.models import GenerationProfile, GenerationResult
from app.ai.scheduler import PriorityInferenceScheduler, InferencePriority
from app.core.exceptions import LLMError


class LLMManager:
    """Coordinates registration and switching of active AI LLM providers."""

    def __init__(self, scheduler: PriorityInferenceScheduler | None = None) -> None:
        """Initializes the LLMManager with empty provider registry.

        Args:
            scheduler: Optional PriorityInferenceScheduler.
        """
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._active_provider_name: str | None = None
        self._scheduler = scheduler

    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """Registers an AI provider in the manager.

        Args:
            name: Unique registration name for the provider.
            provider: Concrete provider instance.
        """
        self._providers[name] = provider

    def remove_provider(self, name: str) -> None:
        """Removes a registered LLM provider.

        Args:
            name: Name of the provider to remove.
        """
        if name in self._providers:
            del self._providers[name]
        if self._active_provider_name == name:
            self._active_provider_name = None

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

    def load_provider(self, name: str) -> None:
        """Switches to the specified provider and initializes it.

        Args:
            name: Name of the registered provider.

        Raises:
            LLMError: If initialization fails.
        """
        self.switch_provider(name)
        active = self.active_provider
        if active:
            try:
                active.initialize()
            except Exception as e:
                raise LLMError(f"Failed to initialize provider '{name}': {e}") from e

    def reload_provider(self, name: str) -> None:
        """Re-initializes a registered provider.

        Args:
            name: Name of the provider to reload.

        Raises:
            LLMError: If re-initialization fails.
            KeyError: If the provider is not registered.
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' is not registered.")
        provider = self._providers[name]
        try:
            provider.shutdown()
            provider.initialize()
        except Exception as e:
            raise LLMError(f"Failed to reload provider '{name}': {e}") from e

    @property
    def active_provider(self) -> BaseLLMProvider | None:
        """Retrieves the active LLM provider instance."""
        return self.get_active_provider()

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

    def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED,
        priority: InferencePriority = InferencePriority.FOREGROUND
    ) -> GenerationResult:
        """Delegates generation to the active provider.

        Args:
            messages: Formatted message payload dictionaries.
            options: Optional runtime options.
            tools: Optional provider-neutral tool schemas list.
            profile: Optional semantic generation profile.
            priority: Inference scheduling priority.

        Returns:
            GenerationResult: Wrapped response and normalized metrics.

        Raises:
            LLMError: If no provider is active or generation fails.
        """
        active = self.active_provider
        if not active:
            raise LLMError("No active LLM provider has been loaded.")
        
        if self._scheduler and threading.current_thread() != self._scheduler.worker_thread:
            return self._scheduler.execute(
                lambda: active.generate(messages, options, tools, profile),
                priority=priority
            )
        return active.generate(messages, options, tools, profile)

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED
    ) -> Iterator[Any]:
        """Delegates streaming generation to the active provider.

        Args:
            messages: Formatted message payload dictionaries.
            options: Optional runtime options.
            tools: Optional provider-neutral tool schemas list.
            profile: Optional semantic generation profile.

        Returns:
            Iterator[Any]: An iterator yielding raw provider response chunks.

        Raises:
            LLMError: If no provider is active or generation fails.
        """
        active = self.active_provider
        if not active:
            raise LLMError("No active LLM provider has been loaded.")
        return active.generate_stream(messages, options, tools, profile)

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
