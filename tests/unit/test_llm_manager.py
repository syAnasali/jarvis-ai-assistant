"""Unit tests for LLMManager scheduler integration."""

import pytest
from unittest.mock import MagicMock
from app.ai.interfaces import BaseLLMProvider
from app.ai.models import GenerationProfile, GenerationResult, GenerationMetrics
from app.ai.scheduler import PriorityInferenceScheduler, InferencePriority
from app.ai.manager import LLMManager
from app.core.exceptions import LLMError


class FakeProvider(BaseLLMProvider):
    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def generate(self, messages, options=None, tools=None, profile=GenerationProfile.BALANCED):
        # Return a standard GenerationResult
        metrics = GenerationMetrics(
            provider="fake",
            model="fake-model",
            total_duration_ms=10.0,
            load_duration_ms=0.0,
            prompt_eval_duration_ms=0.0,
            generation_duration_ms=10.0,
            prompt_tokens=5,
            generated_tokens=10,
            tokens_per_second=1000.0,
            generation_profile=profile.value,
            metadata={}
        )
        return GenerationResult(raw_response="Response Text", metrics=metrics)

    def generate_stream(self, messages, options=None, tools=None, profile=GenerationProfile.BALANCED):
        yield "chunk"

    def health_check(self) -> dict:
        return {"status": "ok"}


def test_llm_manager_defaults_to_foreground():
    """Verify that LLMManager.generate defaults to FOREGROUND priority."""
    mock_scheduler = MagicMock(spec=PriorityInferenceScheduler)
    # Set mock_scheduler.execute to run the operation directly and return its result
    mock_scheduler.execute.side_effect = lambda op, priority: op()

    provider = FakeProvider()
    manager = LLMManager(scheduler=mock_scheduler)
    manager.register_provider("fake", provider)
    manager.switch_provider("fake")

    messages = [{"role": "user", "content": "hello"}]
    res = manager.generate(messages)

    assert res.raw_response == "Response Text"
    mock_scheduler.execute.assert_called_once()
    assert mock_scheduler.execute.call_args[1]["priority"] == InferencePriority.FOREGROUND


def test_llm_manager_propagates_explicit_priority():
    """Verify that LLMManager.generate propagates the explicitly passed priority."""
    mock_scheduler = MagicMock(spec=PriorityInferenceScheduler)
    mock_scheduler.execute.side_effect = lambda op, priority: op()

    provider = FakeProvider()
    manager = LLMManager(scheduler=mock_scheduler)
    manager.register_provider("fake", provider)
    manager.switch_provider("fake")

    messages = [{"role": "user", "content": "hello"}]
    
    # Check MEMORY_EXTRACTION priority
    manager.generate(messages, priority=InferencePriority.MEMORY_EXTRACTION)
    mock_scheduler.execute.assert_called_once()
    assert mock_scheduler.execute.call_args[1]["priority"] == InferencePriority.MEMORY_EXTRACTION

    # Check MEMORY_RESOLUTION priority
    mock_scheduler.execute.reset_mock()
    manager.generate(messages, priority=InferencePriority.MEMORY_RESOLUTION)
    mock_scheduler.execute.assert_called_once()
    assert mock_scheduler.execute.call_args[1]["priority"] == InferencePriority.MEMORY_RESOLUTION


def test_llm_manager_returns_result_and_exception_unchanged():
    """Verify that results and exceptions propagate transparently through scheduler."""
    mock_scheduler = MagicMock(spec=PriorityInferenceScheduler)
    mock_scheduler.execute.side_effect = lambda op, priority: op()

    provider = MagicMock(spec=BaseLLMProvider)
    # Configure provider to raise ValueError
    provider.generate.side_effect = ValueError("Database locked")

    manager = LLMManager(scheduler=mock_scheduler)
    manager.register_provider("mock", provider)
    manager.switch_provider("mock")

    messages = [{"role": "user", "content": "hello"}]

    with pytest.raises(ValueError, match="Database locked"):
        manager.generate(messages)


def test_llm_manager_does_not_mutate_messages_and_options():
    """Verify that messages and options dictionaries are not mutated by LLMManager."""
    mock_scheduler = MagicMock(spec=PriorityInferenceScheduler)
    mock_scheduler.execute.side_effect = lambda op, priority: op()

    provider = FakeProvider()
    manager = LLMManager(scheduler=mock_scheduler)
    manager.register_provider("fake", provider)
    manager.switch_provider("fake")

    messages = [{"role": "user", "content": "hello"}]
    options = {"temperature": 0.7}
    
    messages_copy = list(messages)
    options_copy = dict(options)

    manager.generate(messages, options=options)

    assert messages == messages_copy
    assert options == options_copy


def test_agent_runner_priority_propagation():
    """Verify that AgentRunner calls LLMManager with FOREGROUND priority."""
    from app.agent.runner import AgentRunner
    from app.tools.registry import ToolRegistry
    from app.tools.executor import ToolExecutor
    from app.ai.parser import ResponseParser

    mock_llm = MagicMock(spec=LLMManager)
    # Mock generate to return a dummy GenerationResult
    from app.ai.providers.ollama import OllamaProvider
    dummy_result = FakeProvider().generate([])
    mock_llm.generate.return_value = dummy_result

    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    parser = ResponseParser()

    runner = AgentRunner(mock_llm, registry, executor, parser)

    from app.agent.models import AgentRequest
    from datetime import datetime, timezone
    req = AgentRequest("r_1", "hello", "user", datetime.now(timezone.utc), {})

    try:
        runner.run(req, [])
    except Exception:
        # We don't care if it fails later in processing, we only want to assert the generate call
        pass

    mock_llm.generate.assert_called()
    # Check that it was called with priority=FOREGROUND
    args, kwargs = mock_llm.generate.call_args
    assert kwargs.get("priority") == InferencePriority.FOREGROUND


def test_memory_extractor_priority_propagation():
    """Verify that LLMMemoryExtractor calls LLMManager with MEMORY_EXTRACTION priority."""
    from app.memory.extraction import LLMMemoryExtractor
    from app.ai.prompts import PromptManager

    mock_llm = MagicMock(spec=LLMManager)
    dummy_result = FakeProvider().generate([])
    mock_llm.generate.return_value = dummy_result

    prompt_manager = PromptManager()
    extractor = LLMMemoryExtractor(mock_llm, prompt_manager)

    try:
        extractor.extract("I live in Jaipur")
    except Exception:
        pass

    mock_llm.generate.assert_called_once()
    args, kwargs = mock_llm.generate.call_args
    assert kwargs.get("priority") == InferencePriority.MEMORY_EXTRACTION


def test_memory_resolver_priority_propagation():
    """Verify that LLMMemoryResolver calls LLMManager with MEMORY_RESOLUTION priority."""
    from app.memory.resolver import LLMMemoryResolver
    from app.memory.models import MemoryCandidate, MemoryType, MemorySource

    mock_llm = MagicMock(spec=LLMManager)
    dummy_result = FakeProvider().generate([])
    mock_llm.generate.return_value = dummy_result

    resolver = LLMMemoryResolver(mock_llm)
    from app.memory.models import Memory
    from datetime import datetime, timezone
    cand = MemoryCandidate("The user prefers JS.", MemoryType.PREFERENCE, 0.8, 0.9, MemorySource.USER, "I prefer JS", {})
    existing = Memory("mem_1", "The user prefers Python.", MemoryType.PREFERENCE, datetime.now(timezone.utc), datetime.now(timezone.utc), 0.8, MemorySource.USER, {})

    resolver.resolve(cand, [existing])

    mock_llm.generate.assert_called_once()
    args, kwargs = mock_llm.generate.call_args
    assert kwargs.get("priority") == InferencePriority.MEMORY_RESOLUTION

