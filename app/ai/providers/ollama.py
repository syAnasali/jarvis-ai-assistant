"""Ollama LLM provider implementation."""

from collections.abc import Iterator
from typing import List, Dict, Any
from ollama import Client, ResponseError
from app.ai.interfaces import BaseLLMProvider
from app.core.exceptions import LLMError


class OllamaProvider(BaseLLMProvider):
    """Concrete implementation of BaseLLMProvider using the Ollama service."""

    def __init__(self, host: str, model: str) -> None:
        """Initializes the OllamaProvider.

        Args:
            host: The Ollama server host URL.
            model: The name of the LLM model to run.
        """
        self._host = host
        self._model = model
        self._client: Client | None = None

    def initialize(self) -> None:
        """Verifies server connectivity and loads/verifies the configured model.

        Raises:
            LLMError: If server connection fails or model is not loaded.
        """
        try:
            self._client = Client(host=self._host)
            self._verify_model_exists()
        except Exception as e:
            if isinstance(e, LLMError):
                raise e
            raise LLMError(f"Failed to initialize Ollama provider: {e}") from e

    def shutdown(self) -> None:
        """Closes connections and releases references to the client. Idempotent."""
        if self._client is not None:
            self._client = None

    def is_available(self) -> bool:
        """Verifies if the Ollama server is reachable and active.

        Returns:
            bool: True if server responds, False otherwise.
        """
        if self._client is None:
            return False
        try:
            self._client.list()
            return True
        except Exception:
            return False

    def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None
    ) -> Any:
        """Performs a chat completion request to the Ollama server.

        Args:
            messages: Formatted message payload dictionaries.
            options: Optional execution options.

        Returns:
            Any: Raw Ollama chat response object or dictionary.

        Raises:
            LLMError: If the chat completion fails.
        """
        if self._client is None:
            raise LLMError("Ollama client is not initialized. Call initialize() first.")

        try:
            response = self._client.chat(
                model=self._model,
                messages=messages,
                options=options,
            )
            return response
        except ResponseError as e:
            raise LLMError(f"Ollama API returned an error: {e}") from e
        except Exception as e:
            raise LLMError(f"Ollama generation failed: {e}") from e

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None
    ) -> Iterator[Any]:
        """Performs a streaming chat completion request to the Ollama server.

        Args:
            messages: Formatted message payload dictionaries.
            options: Optional execution options.

        Returns:
            Iterator[Any]: An iterator yielding raw Ollama response chunks.

        Raises:
            LLMError: If the streaming request fails.
        """
        if self._client is None:
            raise LLMError("Ollama client is not initialized. Call initialize() first.")

        try:
            stream = self._client.chat(
                model=self._model,
                messages=messages,
                options=options,
                stream=True,
            )
            for chunk in stream:
                yield chunk
        except ResponseError as e:
            raise LLMError(f"Ollama API returned a streaming error: {e}") from e
        except Exception as e:
            raise LLMError(f"Ollama streaming generation failed: {e}") from e

    def health_check(self) -> Dict[str, Any]:
        """Provides diagnostic information about Ollama connection and model.

        Returns:
            Dict[str, Any]: Diagnostic mapping keys.
        """
        connected = False
        model_exists = False
        if self._client is not None:
            try:
                installed = self._get_installed_models()
                connected = True
                model_exists = self._model in installed or f"{self._model}:latest" in installed
            except Exception:
                pass

        return {
            "provider": "ollama",
            "connected": connected,
            "model": self._model,
            "model_exists": model_exists,
            "host": self._host,
            "available": connected and model_exists
        }

    def _get_installed_models(self) -> List[str]:
        """Retrieves and normalizes the list of installed model names.

        Returns:
            List[str]: List of model names.

        Raises:
            LLMError: If communication with the server fails.
        """
        if not self._client:
            raise LLMError("Ollama client is not initialized.")
        try:
            response = self._client.list()
            models_list = []
            
            # Support both SDK list response objects and dictionary responses
            if isinstance(response, dict):
                models = response.get("models", [])
            else:
                models = getattr(response, "models", [])

            for m in models:
                name = ""
                if isinstance(m, dict):
                    name = m.get("name") or m.get("model") or ""
                else:
                    name = getattr(m, "model", None) or getattr(m, "name", None) or ""
                if name:
                    models_list.append(name)
            return models_list
        except Exception as e:
            raise LLMError(f"Failed to retrieve installed models: {e}") from e

    def _verify_model_exists(self) -> None:
        """Verifies configured model exists on the server, raising an error otherwise.

        Raises:
            LLMError: If model is missing or list retrieval fails.
        """
        installed = self._get_installed_models()
        if self._model in installed or f"{self._model}:latest" in installed:
            return

        installed_str = "\n".join(f"- {m}" for m in installed)
        raise LLMError(
            f"Configured model '{self._model}' was not found on the Ollama server at '{self._host}'.\n"
            f"Installed models:\n{installed_str if installed_str else '- None'}\n\n"
            f"Suggested Fix:\n"
            f"  Change OLLAMA_MODEL in .env\n"
            f"  or\n"
            f"  Run: ollama pull {self._model}"
        )
