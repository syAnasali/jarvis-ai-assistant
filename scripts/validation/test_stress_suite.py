#!/usr/bin/env python3
"""Stress Test Validation Suite for Jarvis AI Assistant.

Diagnoses system stability, memory limits, concurrency, and performance under stress.
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from app.core.application import Application
from app.conversation.models import ConversationSession, SessionStatus
from app.agent.messages import Message, MessageRole
from app.agent.models import AgentRequest, ToolCall
from app.ai.models import GenerationResult, GenerationMetrics
from app.tools.models import ToolPermission


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def setup_test_app():
    app = Application()
    app.initialize()
    try:
        app._initialize_llm()
    except Exception:
        from app.ai.manager import LLMManager
        llm_manager = LLMManager()
        mock_provider = MagicMock()
        mock_provider.initialize.return_value = None
        llm_manager.register_provider("mock", mock_provider)
        llm_manager.switch_provider("mock")
        app.container.register("llm_manager", llm_manager)
    app._initialize_agent()
    return app


def test_stress_long_conversations():
    safe_print("=== Stress Test 1: Long Conversations (100 Turns) ===")
    app = setup_test_app()
    from app.utils.id_generator import generate_message_id
    conv_mgr = app.container.get("conversation_manager")
    policy = app.container.get("conversation_context_policy")
    session = conv_mgr.create_session()

    start_time = time.perf_counter()
    for i in range(100):
        conv_mgr.add_message(session.session_id, Message(id=generate_message_id(), role=MessageRole.USER, content=f"User turn {i} question"))
        conv_mgr.add_message(session.session_id, Message(id=generate_message_id(), role=MessageRole.ASSISTANT, content=f"Assistant turn {i} response answer text"))

    history = conv_mgr.get_messages(session.session_id)
    assert len(history) == 200

    # Test context window policy bounding
    history_bounded, used, skipped = policy.select_history_with_diagnostics(history)
    duration_ms = (time.perf_counter() - start_time) * 1000

    from app.config.settings import settings
    assert used <= settings.conversation_context_max_messages
    assert skipped == 200 - used
    safe_print(f"PASS: 100 turns (200 msgs) stored and trimmed to {used} used, {skipped} skipped in {duration_ms:.2f} ms.")
    app.shutdown()


def test_stress_large_memory_database():
    safe_print("\n=== Stress Test 2: Large Memory Database (1,000 Entries) ===")
    app = setup_test_app()
    from app.memory.models import MemoryType, MemorySource
    memory_mgr = app.container.get("memory_manager")
    retriever = app.container.get("memory_retriever")

    start_time = time.perf_counter()
    for i in range(1000):
        memory_mgr.create_memory(
            content=f"User preference detail value {i}",
            memory_type=MemoryType.PREFERENCE,
            importance=0.5,
            source=MemorySource.USER
        )
    
    write_ms = (time.perf_counter() - start_time) * 1000

    query_start = time.perf_counter()
    res = retriever.retrieve("preference detail 500")
    query_ms = (time.perf_counter() - query_start) * 1000

    assert len(res.matches) > 0
    safe_print(f"PASS: 1,000 memories written in {write_ms:.2f} ms; query recalled match in {query_ms:.2f} ms.")
    app.shutdown()


def test_stress_repeated_tool_execution():
    safe_print("\n=== Stress Test 3: Repeated Tool Execution (50 Calls) ===")
    app = setup_test_app()
    executor = app.container.get("tool_executor")

    tool_call = ToolCall(tool_name="get_current_time", arguments={})

    start_time = time.perf_counter()
    for _ in range(50):
        res = executor.execute(tool_call)
        assert res.success is True
    
    total_ms = (time.perf_counter() - start_time) * 1000
    avg_ms = total_ms / 50.0

    safe_print(f"PASS: 50 back-to-back tool executions completed in {total_ms:.2f} ms (avg {avg_ms:.2f} ms/call).")
    app.shutdown()


def test_stress_rapid_user_requests():
    safe_print("\n=== Stress Test 4: Rapid User Requests (20 Requests) ===")
    app = setup_test_app()
    controller = app.container.get("controller")

    raw_resp = {"message": {"role": "assistant", "content": "Rapid response answer."}}
    app.container.get("llm_manager").generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp,
        metrics=GenerationMetrics(provider="mock", model="mock")
    ))

    start_time = time.perf_counter()
    for i in range(20):
        req = AgentRequest(request_id=f"req_stress_{i}", text=f"Rapid request {i}", source="test")
        resp = controller.process_request(req)
        assert resp.success is True

    total_ms = (time.perf_counter() - start_time) * 1000
    avg_ms = total_ms / 20.0

    safe_print(f"PASS: 20 rapid requests processed in {total_ms:.2f} ms (avg {avg_ms:.2f} ms/req).")
    app.shutdown()


def test_stress_large_filesystem_operations():
    safe_print("\n=== Stress Test 5: Large Filesystem Operations (80KB File Buffer) ===")
    app = setup_test_app()
    fs_service = app.container.get("filesystem_service")

    # Generate 80KB text string (within policy limit of 100KB)
    chunk = "A" * 1024  # 1KB
    large_content = chunk * 80  # 80KB

    start_time = time.perf_counter()
    fs_service.write_text_file("Temp", "large_stress_file.txt", large_content)
    write_ms = (time.perf_counter() - start_time) * 1000

    read_start = time.perf_counter()
    target = fs_service._resolver.resolve("Temp", "large_stress_file.txt")
    read_back = target.resolved_path.read_text(encoding="utf-8")
    read_ms = (time.perf_counter() - read_start) * 1000

    assert len(read_back) == len(large_content)
    safe_print(f"PASS: 80KB file written in {write_ms:.2f} ms and read back in {read_ms:.2f} ms.")

    fs_service.delete_path("Temp", "large_stress_file.txt")
    app.shutdown()


def test_stress_repeated_approvals():
    safe_print("\n=== Stress Test 6: Repeated Approvals (20 Actions) ===")
    app = setup_test_app()
    approval_mgr = app.container.get("approval_manager")

    actions = []
    start_time = time.perf_counter()
    for i in range(20):
        act = approval_mgr.create_pending_action(
            tool_name="create_file",
            arguments={"root": "Temp", "relative_path": f"appr_{i}.txt", "content": "x"},
            permission_level=ToolPermission.CONFIRMATION,
            reason=f"Test approval {i}"
        )
        actions.append(act)

    for act in actions:
        approval_mgr.approve(act.action_id)

    total_ms = (time.perf_counter() - start_time) * 1000
    safe_print(f"PASS: 20 pending actions created and approved in {total_ms:.2f} ms.")
    app.shutdown()


def test_stress_streaming_stability():
    safe_print("\n=== Stress Test 7: Streaming Stability (500 Chunks) ===")
    app = setup_test_app()
    controller = app.container.get("controller")

    chunks = [{"message": {"content": f"chunk_{i} "}} for i in range(500)]
    mock_provider = MagicMock()
    mock_provider.generate_stream.return_value = iter(chunks)
    mock_provider.initialize.return_value = None
    mock_provider.shutdown.return_value = None

    llm_manager = app.container.get("llm_manager")
    llm_manager.register_provider("stream_mock", mock_provider)
    llm_manager.switch_provider("stream_mock")

    req = AgentRequest(request_id="req_stream_stress", text="Stream long response", source="test")
    
    stream_chunks = list(controller.process_request_stream(req))
    assert len(stream_chunks) > 0
    safe_print(f"PASS: Streaming stability verified across {len(stream_chunks)} streamed output chunks.")
    app.shutdown()


def run_all_stress_tests():
    safe_print("============================================================")
    safe_print("STARTING STRESS TEST VALIDATION SUITE")
    safe_print("============================================================")

    test_stress_long_conversations()
    test_stress_large_memory_database()
    test_stress_repeated_tool_execution()
    test_stress_rapid_user_requests()
    test_stress_large_filesystem_operations()
    test_stress_repeated_approvals()
    test_stress_streaming_stability()

    safe_print("\n============================================================")
    safe_print("ALL STRESS TESTS PASSED SUCCESSFULLY!")
    safe_print("============================================================")


if __name__ == "__main__":
    run_all_stress_tests()
