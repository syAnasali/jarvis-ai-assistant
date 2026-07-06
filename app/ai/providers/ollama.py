"""Ollama LLM provider implementation."""

import threading
from collections.abc import Iterator
from typing import List, Dict, Any
from ollama import Client, ResponseError
from app.ai.interfaces import BaseLLMProvider
from app.ai.models import GenerationMetrics, GenerationResult, GenerationProfile
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
        self._lock = threading.Lock()

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

    def _adapt_generation_profile(
        self,
        profile: GenerationProfile,
        options: Dict[str, Any] | None
    ) -> tuple[bool | None, Dict[str, Any]]:
        """Maps provider-neutral GenerationProfile to Ollama specific options and settings.

        Precedence:
            Profile defaults are applied first. Explicit caller-provided options
            override defaults. This method does not mutate the input dictionary.

        Args:
            profile: Semantic GenerationProfile value.
            options: Caller-provided runtime options.

        Returns:
            tuple[bool | None, Dict[str, Any]]: Think parameter value and merged options dictionary.
        """
        merged_options = {}
        if options:
            merged_options.update(options)

        # For qwen3:8b in Ollama:
        if profile == GenerationProfile.FAST:
            think_value = False
        elif profile == GenerationProfile.TOOL_SELECTION:
            think_value = False
        elif profile == GenerationProfile.BALANCED:
            think_value = False
        elif profile == GenerationProfile.REASONING:
            think_value = True
        elif profile == GenerationProfile.MEMORY_EXTRACTION:
            think_value = False
            # Default options for structured memory extraction
            if "temperature" not in merged_options:
                merged_options["temperature"] = 0.0
            if "num_predict" not in merged_options:
                merged_options["num_predict"] = 256
            if "format" not in merged_options:
                merged_options["format"] = "json"
        else:
            think_value = None

        from app.core.logger import JarvisLogger
        prov_logger = JarvisLogger.get_logger("ollama_provider")
        prov_logger.debug(f"Resolved provider profile behaviour: profile={profile.name}, think={think_value}")

        return think_value, merged_options

    def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED
    ) -> GenerationResult:
        """Performs a chat completion request to the Ollama server.

        Args:
            messages: Formatted message payload dictionaries.
            options: Optional execution options.
            tools: Optional provider-neutral tool schemas list.
            profile: Optional semantic generation profile.

        Returns:
            GenerationResult: Wrapped response and normalized metrics.

        Raises:
            LLMError: If the chat completion fails.
        """
        if self._client is None:
            raise LLMError("Ollama client is not initialized. Call initialize() first.")

        kwargs: Dict[str, Any] = {}
        think_value, merged_options = self._adapt_generation_profile(profile, options)
        if merged_options:
            if "format" in merged_options:
                kwargs["format"] = merged_options.pop("format")
            if merged_options:
                kwargs["options"] = merged_options
        if think_value is not None:
            kwargs["think"] = think_value

        if tools:
            adapted = []
            for t in tools:
                adapted.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description"),
                        "parameters": t.get("parameters", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    }
                })
            kwargs["tools"] = adapted

        try:
            with self._lock:
                response = self._client.chat(
                    model=self._model,
                    messages=messages,
                    **kwargs
                )
            
            # Helper to retrieve metric safely
            def get_metric(obj: Any, key: str) -> Any:
                if isinstance(obj, dict):
                    return obj.get(key)
                return getattr(obj, key, None)

            def to_ms(ns: Any) -> float | None:
                if ns is None:
                    return None
                try:
                    return float(ns) / 1_000_000.0
                except (ValueError, TypeError):
                    return None

            total_duration_ms = to_ms(get_metric(response, "total_duration"))
            load_duration_ms = to_ms(get_metric(response, "load_duration"))
            prompt_eval_duration_ms = to_ms(get_metric(response, "prompt_eval_duration"))
            generation_duration_ms = to_ms(get_metric(response, "eval_duration"))
            
            p_tokens = get_metric(response, "prompt_eval_count")
            g_tokens = get_metric(response, "eval_count")
            
            # Calculate tokens per second
            tokens_per_second = None
            eval_ns = get_metric(response, "eval_duration")
            if g_tokens is not None and eval_ns is not None:
                try:
                    gen_sec = float(eval_ns) / 1_000_000_000.0
                    if gen_sec > 0:
                        tokens_per_second = float(g_tokens) / gen_sec
                except (ValueError, TypeError, ZeroDivisionError):
                    pass

            metrics = GenerationMetrics(
                provider="ollama",
                model=get_metric(response, "model") or self._model,
                total_duration_ms=total_duration_ms,
                load_duration_ms=load_duration_ms,
                prompt_eval_duration_ms=prompt_eval_duration_ms,
                generation_duration_ms=generation_duration_ms,
                prompt_tokens=p_tokens,
                generated_tokens=g_tokens,
                tokens_per_second=tokens_per_second,
                generation_profile=profile.value,
                metadata=response if isinstance(response, dict) else getattr(response, "__dict__", {})
            )

            return GenerationResult(raw_response=response, metrics=metrics)
        except ResponseError as e:
            raise LLMError(f"Ollama API returned an error: {e}") from e
        except Exception as e:
            raise LLMError(f"Ollama generation failed: {e}") from e

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED
    ) -> Iterator[Any]:
        """Performs a streaming chat completion request to the Ollama server.

        Args:
            messages: Formatted message payload dictionaries.
            options: Optional execution options.
            tools: Optional provider-neutral tool schemas list.
            profile: Optional semantic generation profile.

        Returns:
            Iterator[Any]: An iterator yielding raw Ollama response chunks.

        Raises:
            LLMError: If the streaming request fails.
        """
        if self._client is None:
            raise LLMError("Ollama client is not initialized. Call initialize() first.")

        kwargs: Dict[str, Any] = {}
        think_value, merged_options = self._adapt_generation_profile(profile, options)
        if merged_options:
            if "format" in merged_options:
                kwargs["format"] = merged_options.pop("format")
            if merged_options:
                kwargs["options"] = merged_options
        if think_value is not None:
            kwargs["think"] = think_value

        if tools:
            adapted = []
            for t in tools:
                adapted.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description"),
                        "parameters": t.get("parameters", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    }
                })
            kwargs["tools"] = adapted

        self._lock.acquire()
        try:
            stream = self._client.chat(
                model=self._model,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            def generator_wrapper() -> Iterator[Any]:
                try:
                    for chunk in stream:
                        yield chunk
                finally:
                    self._lock.release()

            return generator_wrapper()
        except ResponseError as e:
            self._lock.release()
            raise LLMError(f"Ollama API returned a streaming error: {e}") from e
        except Exception as e:
            self._lock.release()
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
