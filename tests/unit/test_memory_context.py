"""Unit tests for the memory context construction."""

from datetime import datetime, timezone
from app.memory.models import Memory, MemoryType, MemorySource, MemoryMatch
from app.memory.context import MemoryContextBuilder, MEMORY_CONTEXT_MARKER


def create_test_match(memory_id: str, content: str, relevance: float = 0.5) -> MemoryMatch:
    """Helper to create dummy MemoryMatch objects."""
    mem = Memory(
        memory_id=memory_id,
        content=content,
        memory_type=MemoryType.FACT,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=0.5,
        source=MemorySource.MANUAL,
        metadata={}
    )
    return MemoryMatch(
        memory=mem,
        relevance_score=relevance,
        lexical_score=0.5,
        importance_score=0.5
    )


def test_empty_matches_produce_no_context():
    """Verify empty matches list produces an empty string."""
    builder = MemoryContextBuilder()
    assert builder.build([]) == ""


def test_stable_memory_marker_exists():
    """Verify the stable context semantic marker exists in the context."""
    builder = MemoryContextBuilder()
    match = create_test_match("mem_1", "The user's name is Anas.")
    context = builder.build([match])
    
    assert MEMORY_CONTEXT_MARKER in context
    assert f"[{MEMORY_CONTEXT_MARKER}]" in context


def test_selected_memories_appear_in_context():
    """Verify the contents of matches appear in the output."""
    builder = MemoryContextBuilder()
    match = create_test_match("mem_1", "Anas is building a software tool.")
    context = builder.build([match])
    
    assert "- Anas is building a software tool." in context


def test_scores_do_not_appear_in_context():
    """Verify relevance, lexical, and importance scores are NOT exposed to the model."""
    builder = MemoryContextBuilder()
    match = create_test_match("mem_1", "Anas is building a software tool.", relevance=0.9876)
    context = builder.build([match])
    
    assert "0.9876" not in context
    assert "0.5" not in context


def test_maximum_memory_count_enforced():
    """Verify max memories count constraint is respected."""
    # Max count: 2
    builder = MemoryContextBuilder(max_memories=2)
    matches = [
        create_test_match("m1", "Fact A"),
        create_test_match("m2", "Fact B"),
        create_test_match("m3", "Fact C")
    ]
    
    context = builder.build(matches)
    assert "- Fact A" in context
    assert "- Fact B" in context
    assert "- Fact C" not in context


def test_maximum_character_bound_enforced():
    """Verify max character limit excludes the next memory cleanly without truncation."""
    # Header size is around 325 characters. Let's make character limit small enough to fit only 1 fact
    # Fact 1: 8 characters + 1 newline -> 9 chars
    # Fact 2: 8 characters + 1 newline -> 9 chars
    # Set limit to header size + 12 chars
    match1 = create_test_match("m1", "Fact A")
    match2 = create_test_match("m2", "Fact B")
    
    dummy_header_builder = MemoryContextBuilder(max_characters=1000)
    header_len = len(dummy_header_builder.build([match1])) - len("- Fact A") - 1
    
    # Set limit so only match1 fits
    builder = MemoryContextBuilder(max_characters=header_len + len("- Fact A") + 1 + 5)
    context = builder.build([match1, match2])
    
    assert "- Fact A" in context
    assert "- Fact B" not in context


def test_memory_ordering_preserved_and_output_deterministic():
    """Verify ordering of matches is preserved in context formatting."""
    builder = MemoryContextBuilder()
    matches = [
        create_test_match("m1", "First match"),
        create_test_match("m2", "Second match"),
        create_test_match("m3", "Third match")
    ]
    
    context = builder.build(matches)
    
    pos1 = context.find("First match")
    pos2 = context.find("Second match")
    pos3 = context.find("Third match")
    
    assert pos1 < pos2 < pos3
    # Run again to verify determinism
    assert builder.build(matches) == context
