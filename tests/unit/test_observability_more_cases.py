"""Additional comprehensive unit tests for Observability Subsystem."""

import pytest
from app.observability.models import SubsystemName, SpanStatus
from app.observability.manager import ObservabilityManager
from app.observability.exceptions import ObservabilityError, MetricsError


def test_subsystem_name_enum():
    assert SubsystemName.LLM.value == "llm"
    assert SubsystemName.AGENT.value == "agent"
    assert SubsystemName.MEMORY.value == "memory"
    assert SubsystemName.KNOWLEDGE.value == "knowledge"
    assert SubsystemName.PLANNER.value == "planner"
    assert SubsystemName.VOICE.value == "voice"
    assert SubsystemName.VISION.value == "vision"
    assert SubsystemName.PLUGIN.value == "plugin"


def test_observability_export_unsupported_format():
    mgr = ObservabilityManager(persistence_enabled=False)
    with pytest.raises(ValueError):
        mgr.export("unsupported_fmt", "path.xml")
