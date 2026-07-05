"""Unit tests for GenerationProfile models, options merging, and propagation."""

import pytest
from typing import Any, List, Dict
from app.ai.models import GenerationProfile, GenerationMetrics, GenerationResult
from app.ai.interfaces import BaseLLMProvider
from app.ai.manager import LLMManager


class DummyProvider(BaseLLMProvider):
    """Dummy provider for testing profile propagation."""

    def __init__(self) -> None:
        self.received_profiles: List[GenerationProfile] = []
        self.received_options: List[Dict[str, Any]] = []

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED
    ) -> GenerationResult:
        self.received_profiles.append(profile)
        self.received_options.append(options or {})
        metrics = GenerationMetrics(
            provider="dummy",
            model="dummy_model",
            generation_profile=profile.value
        )
        return GenerationResult(raw_response={}, metrics=metrics)

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        tools: List[Dict[str, Any]] | None = None,
        profile: GenerationProfile = GenerationProfile.BALANCED
    ) -> Any:
        self.received_profiles.append(profile)
        self.received_options.append(options or {})
        return []

    def health_check(self) -> Dict[str, Any]:
        return {}


def test_generation_profile_values():
    """Verifies the existence and values of the GenerationProfile enum."""
    assert GenerationProfile.FAST.value == "fast"
    assert GenerationProfile.TOOL_SELECTION.value == "tool_selection"
    assert GenerationProfile.BALANCED.value == "balanced"
    assert GenerationProfile.REASONING.value == "reasoning"


def test_profile_propagation_llm_manager():
    """Verifies that the profile propagates correctly from LLMManager to the provider."""
    provider = DummyProvider()
    manager = LLMManager()
    manager.register_provider("dummy", provider)
    manager.switch_provider("dummy")

    # Default profile check
    manager.generate([{"role": "user", "content": "Hi"}])
    assert provider.received_profiles[-1] == GenerationProfile.BALANCED

    # Explicit FAST profile check
    manager.generate([{"role": "user", "content": "Hi"}], profile=GenerationProfile.FAST)
    assert provider.received_profiles[-1] == GenerationProfile.FAST

    # Explicit TOOL_SELECTION profile check
    manager.generate([{"role": "user", "content": "Hi"}], profile=GenerationProfile.TOOL_SELECTION)
    assert provider.received_profiles[-1] == GenerationProfile.TOOL_SELECTION

    # Explicit REASONING profile check
    manager.generate([{"role": "user", "content": "Hi"}], profile=GenerationProfile.REASONING)
    assert provider.received_profiles[-1] == GenerationProfile.REASONING


def test_options_not_mutated_and_deterministic_merging():
    """Verifies options merging is deterministic and caller-provided dictionaries are not mutated."""
    from app.ai.providers.ollama import OllamaProvider

    # Initialize a mock OllamaProvider (don't initialize client)
    provider = OllamaProvider(host="http://localhost:11434", model="qwen3:8b")

    caller_options = {"temperature": 0.7, "num_predict": 100}
    caller_options_copy = dict(caller_options)

    # Adapt profile FAST
    think, merged = provider._adapt_generation_profile(GenerationProfile.FAST, caller_options)
    
    # Assert caller options were not mutated
    assert caller_options == caller_options_copy
    
    # Assert think is False for FAST
    assert think is False
    
    # Assert merged options match caller options since qwen3 has no separate profile-default options
    assert merged == caller_options

    # Verify precedence: caller options override defaults if any defaults existed.
    # Currently qwen3:8b uses think parameter directly. We can verify it returns think=True for REASONING.
    think_reasoning, merged_reasoning = provider._adapt_generation_profile(GenerationProfile.REASONING, caller_options)
    assert think_reasoning is True
    assert merged_reasoning == caller_options
