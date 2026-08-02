#!/usr/bin/env python3
"""Diagnostic verification script for Prompt & Context Optimization."""

import sys
import time
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.agent.messages import Message, MessageRole
from app.conversation.policy import ContextWindowPolicy
from app.memory.models import Memory, MemoryMatch, MemoryType
from app.memory.context import MemoryContextBuilder
from app.tools.filter import ToolFilter
from app.tools.registry import ToolRegistry
from app.ai.prompts import PromptManager
from app.planning.prompts import PLANNER_SYSTEM_PROMPT
from app.core.tracing import RequestTracer


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def test_conversation_context_selection():
    safe_print("=== 1. Testing Conversation Context Selection & Trimming ===")
    policy = ContextWindowPolicy(max_messages=4, max_characters=500)

    messages = [
        Message(id="1", role=MessageRole.USER, content="Hello"),
        Message(id="2", role=MessageRole.ASSISTANT, content="Hi there!"),
        Message(id="3", role=MessageRole.USER, content="What time is it?"),
        Message(id="4", role=MessageRole.ASSISTANT, content="It is 10:00 AM."),
        Message(id="5", role=MessageRole.USER, content="Create a folder named Demo on Desktop"),
    ]

    selected, used_count, skipped_count = policy.select_history_with_diagnostics(messages)

    assert used_count <= 4
    assert skipped_count == len(messages) - used_count
    assert selected[-1].content == "Create a folder named Demo on Desktop"

    safe_print(f"PASS: Context selection retained {used_count} messages, skipped {skipped_count} messages.")


def test_memory_deduplication():
    safe_print("\n=== 2. Testing Memory Deduplication & Filtering ===")
    builder = MemoryContextBuilder(max_memories=5, max_characters=1000)

    from datetime import datetime, timezone
    from app.memory.models import MemorySource
    now = datetime.now(timezone.utc)

    matches = [
        MemoryMatch(memory=Memory(memory_id="m1", content="User prefers Python", memory_type=MemoryType.PREFERENCE, created_at=now, updated_at=now, importance=0.9, source=MemorySource.USER), relevance_score=0.95, lexical_score=0.9, importance_score=0.9),
        MemoryMatch(memory=Memory(memory_id="m2", content="User prefers Python", memory_type=MemoryType.PREFERENCE, created_at=now, updated_at=now, importance=0.9, source=MemorySource.USER), relevance_score=0.90, lexical_score=0.8, importance_score=0.9),  # Duplicate
        MemoryMatch(memory=Memory(memory_id="m3", content="User lives in Seattle", memory_type=MemoryType.FACT, created_at=now, updated_at=now, importance=0.8, source=MemorySource.USER), relevance_score=0.85, lexical_score=0.8, importance_score=0.8),
    ]

    cleaned = builder.deduplicate_and_filter(matches)
    context_str = builder.build(matches)

    assert len(cleaned) == 2
    assert "User prefers Python" in context_str
    assert "User lives in Seattle" in context_str
    assert context_str.count("User prefers Python") == 1

    safe_print("PASS: Duplicate memory entries correctly deduplicated.")


def test_dynamic_tool_filtering():
    safe_print("\n=== 3. Testing Dynamic Tool Schema Filtering ===")
    all_schemas = [
        {"name": "get_current_time"},
        {"name": "get_system_info"},
        {"name": "resolve_application"},
        {"name": "launch_application"},
        {"name": "create_directory"},
        {"name": "create_file"},
        {"name": "write_text_file"},
        {"name": "get_active_window"},
        {"name": "type_text"},
    ]

    # Test 1: Time query -> time tool only
    time_tools = ToolFilter.select_relevant_tools("What time is it right now?", all_schemas)
    assert len(time_tools) == 1
    assert time_tools[0]["name"] == "get_current_time"
    safe_print("PASS: 'What time is it?' filtered down to 1 relevant tool schema.")

    # Test 2: Filesystem query -> filesystem tools only
    fs_tools = ToolFilter.select_relevant_tools("Create folder Demo on Desktop", all_schemas)
    fs_names = [t["name"] for t in fs_tools]
    assert "create_directory" in fs_names
    assert "create_file" in fs_names
    assert "get_current_time" not in fs_names
    safe_print(f"PASS: 'Create folder' filtered down to {len(fs_tools)} filesystem tool schemas.")

    # Test 3: General conversation -> 0 tool schemas
    general_tools = ToolFilter.select_relevant_tools("Hello, how are you today?", all_schemas)
    assert len(general_tools) == 0
    safe_print("PASS: General chat query filtered down to 0 tool schemas.")


def test_system_prompt_caching():
    safe_print("\n=== 4. Testing System Prompt Caching ===")
    pm = PromptManager()
    p1 = pm.system_prompt()
    p2 = pm.system_prompt()
    policy1 = pm.tool_use_policy()
    policy2 = pm.tool_use_policy()

    assert p1 is p2
    assert policy1 is policy2
    safe_print("PASS: System prompts are statically cached in memory.")


def test_planner_prompt_conciseness():
    safe_print("\n=== 5. Testing Concise Planner System Prompt ===")
    formatted_prompt = PLANNER_SYSTEM_PROMPT.format(
        available_tools='[{"name": "create_directory"}]',
        max_steps=5
    )
    assert "JSON ONLY" in formatted_prompt
    assert "PLANNING RULES" in formatted_prompt
    assert len(formatted_prompt) < 1800
    safe_print(f"PASS: Planner system prompt optimized to {len(formatted_prompt)} characters.")


def test_prompt_diagnostics_report():
    safe_print("\n=== 6. Testing Prompt Diagnostics Report ===")
    tracer = RequestTracer(request_id="req_prompt_opt_999", session_id="sess_opt")

    report = tracer.get_prompt_diagnostics_report(
        messages_used=4,
        messages_skipped=2,
        memory_count=2,
        tool_count=1,
        prompt_chars=1200,
        unoptimized_baseline_chars=5700
    )

    assert "Conversation Messages Used:     4" in report
    assert "Conversation Messages Skipped:  2" in report
    assert "Injected Memories Count:        2" in report
    assert "Injected Tool Schemas Count:    1" in report
    assert "Prompt Reduction vs Baseline:" in report

    safe_print(report)
    safe_print("PASS: Prompt Diagnostics Report generated successfully.")


def run_all_prompt_optimization_tests():
    safe_print("============================================================")
    safe_print("STARTING PROMPT & CONTEXT OPTIMIZATION SUITE")
    safe_print("============================================================")

    test_conversation_context_selection()
    test_memory_deduplication()
    test_dynamic_tool_filtering()
    test_system_prompt_caching()
    test_planner_prompt_conciseness()
    test_prompt_diagnostics_report()

    safe_print("\n============================================================")
    safe_print("ALL PROMPT OPTIMIZATION TESTS PASSED SUCCESSFULLY!")
    safe_print("============================================================")


if __name__ == "__main__":
    run_all_prompt_optimization_tests()
