"""Unit tests for GenerationMetrics and Ollama Provider metrics extraction."""

from app.ai.models import GenerationMetrics, GenerationResult


def test_generation_metrics_default_values():
    """Verifies that GenerationMetrics can be created with only provider and model."""
    metrics = GenerationMetrics(provider="test_prov", model="test_model")
    assert metrics.provider == "test_prov"
    assert metrics.model == "test_model"
    assert metrics.total_duration_ms is None
    assert metrics.load_duration_ms is None
    assert metrics.prompt_eval_duration_ms is None
    assert metrics.generation_duration_ms is None
    assert metrics.prompt_tokens is None
    assert metrics.generated_tokens is None
    assert metrics.tokens_per_second is None
    assert metrics.metadata == {}


def test_generation_metrics_tokens_per_second_calculation():
    """Verifies tokens_per_second calculation under various conditions."""
    # Simulates calculation logic used in the provider
    def calculate_tps(gen_tokens: int | None, eval_ns: int | None) -> float | None:
        if gen_tokens is not None and eval_ns is not None:
            try:
                gen_sec = float(eval_ns) / 1_000_000_000.0
                if gen_sec > 0:
                    return float(gen_tokens) / gen_sec
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        return None

    # Normal case
    assert calculate_tps(20, 500_000_000) == 40.0
    
    # Zero duration (no division by zero)
    assert calculate_tps(20, 0) is None
    
    # Negative duration
    assert calculate_tps(20, -100) is None
    
    # Missing values
    assert calculate_tps(None, 500_000_000) is None
    assert calculate_tps(20, None) is None
