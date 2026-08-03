"""Manager for registering and coordinating active LLM providers."""

from collections.abc import Iterator
import threading
import time
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
        self._retry_count = 0
        self._recovery_success_count = 0
        self._provider_reconnect_count = 0

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def recovery_success_count(self) -> int:
        return self._recovery_success_count

    @property
    def provider_reconnect_count(self) -> int:
        return self._provider_reconnect_count

    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """Registers an AI provider in the manager."""
        self._providers[name] = provider

    def remove_provider(self, name: str) -> None:
        """Removes a registered LLM provider."""
        if name in self._providers:
            del self._providers[name]
        if self._active_provider_name == name:
            self._active_provider_name = None

    def switch_provider(self, name: str) -> None:
        """Switches the active provider to the registered provider."""
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' is not registered.")
        self._active_provider_name = name

    def load_provider(self, name: str) -> None:
        """Switches to the specified provider and initializes it."""
        self.switch_provider(name)
        active = self.active_provider
        if active:
            try:
                active.initialize()
            except Exception as e:
                raise LLMError(f"Failed to initialize provider '{name}': {e}") from e

    def reload_provider(self, name: str) -> None:
        """Re-initializes a registered provider."""
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
        """Retrieves the currently active provider instance."""
        if not self._active_provider_name:
            return None
        return self._providers[self._active_provider_name]

    def get_provider(self, name: str) -> BaseLLMProvider:
        """Retrieves a registered provider by name."""
        return self._providers[name]

    def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED,
        priority: InferencePriority = InferencePriority.FOREGROUND
    ) -> GenerationResult:
        """Delegates generation to the active provider with retry and recovery policies.

        Args:
            messages: Formatted message payload dictionaries.
            options: Optional runtime options.
            tools: Optional provider-neutral tool schemas list.
            profile: Optional semantic generation profile.
            priority: Inference scheduling priority.

        Returns:
            GenerationResult: Wrapped response and normalized metrics.

        Raises:
            LLMError: If no provider is active or generation fails after retries.
        """
        active = self.active_provider
        if not active:
            from app.core.exceptions import ProviderUnavailableError
            raise ProviderUnavailableError("No active LLM provider has been loaded.")
        
        from app.config.settings import settings
        from app.core.exceptions import ProviderUnavailableError, ProviderTimeoutError, RecoverableError
        from app.core.logger import JarvisLogger
        logger = JarvisLogger.get_logger("llm_manager")

        max_attempts = max(1, settings.llm_max_retries)
        last_exception = None

        def _do_call():
            return active.generate(messages, options, tools, profile)

        for attempt in range(1, max_attempts + 1):
            try:
                if self._scheduler and threading.current_thread() != self._scheduler.worker_thread:
                    res = self._scheduler.execute(_do_call, priority=priority)
                else:
                    res = _do_call()
                if attempt > 1:
                    self._recovery_success_count += 1
                    logger.info(f"LLM Provider recovered successfully on attempt {attempt}.")
                return res
            except Exception as e:
                last_exception = e
                self._retry_count += 1
                logger.log_error(
                    operation=f"LLM Provider Generation (Attempt {attempt}/{max_attempts})",
                    error=e,
                    user_message="LLM provider connection encountered an issue."
                )

                if attempt < max_attempts:
                    # Attempt provider reconnect/reload before retrying
                    if self._active_provider_name:
                        try:
                            self.reload_provider(self._active_provider_name)
                            self._provider_reconnect_count += 1
                            logger.info(f"Reconnected LLM provider '{self._active_provider_name}' before retry attempt {attempt + 1}.")
                        except Exception as re_err:
                            logger.warning(f"Provider reconnect attempt failed: {re_err}")
                    time.sleep(0.1 * (2 ** (attempt - 1)))

        err_str = str(last_exception)
        if isinstance(last_exception, (ValueError, TypeError, KeyError, AttributeError, AssertionError)) and not any(k in err_str.lower() for k in ("connection", "socket", "timeout", "timed out")):
            raise last_exception
        if "timeout" in err_str.lower() or "timed out" in err_str.lower():
            raise ProviderTimeoutError(f"LLM provider operation timed out after {max_attempts} attempts: {last_exception}") from last_exception
        raise ProviderUnavailableError(f"LLM provider service unavailable after {max_attempts} attempts: {last_exception}") from last_exception

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
            from app.core.exceptions import ProviderUnavailableError
            raise ProviderUnavailableError("No active LLM provider has been loaded.")
        try:
            return active.generate_stream(messages, options, tools, profile)
        except Exception as e:
            from app.core.exceptions import ProviderUnavailableError
            raise ProviderUnavailableError(f"LLM streaming provider error: {e}") from e

    def shutdown(self) -> None:
        """Shuts down all registered providers cleanly."""
        for name, provider in list(self._providers.items()):
            try:
                provider.shutdown()
            except Exception:
                pass

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
