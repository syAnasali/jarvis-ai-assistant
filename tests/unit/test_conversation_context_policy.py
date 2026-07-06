"""Unit tests for ContextWindowPolicy."""

import pytest
from datetime import datetime, timezone, timedelta
from app.agent.messages import Message, MessageRole
from app.conversation.policy import ContextWindowPolicy


def test_empty_history():
    """Verify that an empty list of messages returns an empty selected history."""
    policy = ContextWindowPolicy(max_messages=10, max_characters=1000)
    assert policy.select_history([]) == []


def test_history_below_limits():
    """Verify that history within bounds is returned entirely and unchanged."""
    policy = ContextWindowPolicy(max_messages=5, max_characters=100)
    now = datetime.now(timezone.utc)
    m1 = Message("m1", MessageRole.USER, "Hello", now, {})
    m2 = Message("m2", MessageRole.ASSISTANT, "Hi", now + timedelta(seconds=1), {})

    selected = policy.select_history([m1, m2])
    assert selected == [m1, m2]


def test_message_count_limit():
    """Verify that message count budget limits returned list and keeps chronological order."""
    policy = ContextWindowPolicy(max_messages=3, max_characters=1000)
    now = datetime.now(timezone.utc)
    messages = [
        Message(f"m{i}", MessageRole.USER, f"Msg {i}", now + timedelta(seconds=i), {})
        for i in range(5)
    ]

    selected = policy.select_history(messages)
    # Exceeds max_messages of 3. Should return the last 3: m2, m3, m4
    assert len(selected) == 3
    assert [m.id for m in selected] == ["m2", "m3", "m4"]


def test_character_limit_and_latest_preservation():
    """Verify that character budget excludes older messages while always preserving the latest message whole."""
    policy = ContextWindowPolicy(max_messages=10, max_characters=15)
    now = datetime.now(timezone.utc)
    # Total chars: m1(6), m2(6), m3(6). Limit 15.
    m1 = Message("m1", MessageRole.USER, "Msg 11", now, {})
    m2 = Message("m2", MessageRole.ASSISTANT, "Msg 22", now + timedelta(seconds=1), {})
    m3 = Message("m3", MessageRole.USER, "Msg 33", now + timedelta(seconds=2), {})

    # m3 (latest) has length 6. m2 has length 6 (6 + 6 = 12 <= 15).
    # m1 has length 6 (12 + 6 = 18 > 15). So m1 is excluded.
    # Chronological order of selected: m2, m3
    selected = policy.select_history([m1, m2, m3])
    assert [m.id for m in selected] == ["m2", "m3"]


def test_single_oversized_latest_message_included():
    """Verify that if the latest message alone exceeds character budget, it is still included whole."""
    policy = ContextWindowPolicy(max_messages=10, max_characters=5)
    now = datetime.now(timezone.utc)
    m1 = Message("m1", MessageRole.USER, "Short", now, {})
    m2 = Message("m2", MessageRole.ASSISTANT, "Oversized response", now + timedelta(seconds=1), {})

    # m2 length is 18. max_characters is 5.
    # Latest message (m2) must be preserved.
    selected = policy.select_history([m1, m2])
    assert [m.id for m in selected] == ["m2"]


def test_input_immutability():
    """Verify that select_history does not mutate the input list or message objects."""
    policy = ContextWindowPolicy(max_messages=2, max_characters=20)
    now = datetime.now(timezone.utc)
    m1 = Message("m1", MessageRole.USER, "Content 1", now, {})
    m2 = Message("m2", MessageRole.ASSISTANT, "Content 2", now + timedelta(seconds=1), {})
    m3 = Message("m3", MessageRole.USER, "Content 3", now + timedelta(seconds=2), {})

    original_list = [m1, m2, m3]
    original_list_copy = list(original_list)

    policy.select_history(original_list)

    # Assert that input list structure was not altered
    assert original_list == original_list_copy
    assert m1.content == "Content 1"
    assert m2.content == "Content 2"
    assert m3.content == "Content 3"


def test_deterministic_selection():
    """Verify that selection yields identical results across repeated runs."""
    policy = ContextWindowPolicy(max_messages=2, max_characters=50)
    now = datetime.now(timezone.utc)
    messages = [
        Message(f"m{i}", MessageRole.USER, f"Msg {i}", now + timedelta(seconds=i), {})
        for i in range(4)
    ]

    res1 = policy.select_history(messages)
    res2 = policy.select_history(messages)
    assert res1 == res2
