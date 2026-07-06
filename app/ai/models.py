"""Data models for AI generation results and metrics."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class GenerationProfile(Enum):
    """Semantic generation profile determining latency/quality trade-offs."""

    FAST = "fast"
    TOOL_SELECTION = "tool_selection"
    BALANCED = "balanced"
    REASONING = "reasoning"
    MEMORY_EXTRACTION = "memory_extraction"


@dataclass(frozen=True)
class GenerationMetrics:
    """Provider-neutral metrics describing a model generation request.

    Attributes:
        total_duration_ms: Total duration of the request in milliseconds.
        load_duration_ms: Time spent loading the model into memory.
        prompt_eval_duration_ms: Time spent evaluating the prompt.
        generation_duration_ms: Time spent generating tokens.
        prompt_tokens: Number of tokens in the prompt.
        generated_tokens: Number of generated tokens.
        tokens_per_second: Tokens generated per second.
        provider: The provider name.
        model: The model name.
        generation_profile: The semantic profile used for generation.
        metadata: Unstructured provider-specific metrics metadata.
    """

    provider: str
    model: str
    total_duration_ms: float | None = None
    load_duration_ms: float | None = None
    prompt_eval_duration_ms: float | None = None
    generation_duration_ms: float | None = None
    prompt_tokens: int | None = None
    generated_tokens: int | None = None
    tokens_per_second: float | None = None
    generation_profile: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResult:
    """Wrapper containing the raw response and normalized metrics.

    Attributes:
        raw_response: The raw response payload (e.g. ChatResponse or dict).
        metrics: Normalized GenerationMetrics for the response.
    """

    raw_response: Any
    metrics: GenerationMetrics
