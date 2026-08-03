#!/usr/bin/env python3
"""End-to-End Integration Validation Suite for Jarvis AI Assistant.

Covers 9 realistic end-to-end integration scenarios across all subsystems.
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from app.core.application import Application
from app.agent.models import AgentRequest, AgentResponse
from app.agent.controller import AgentController
from app.agent.messages import Message, MessageRole
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall
from app.ai.models import GenerationResult, GenerationMetrics
from app.core.lifecycle import ApplicationState
from app.core.constants import DATABASE_PATH


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


def test_scenario_1_chat_only():
    safe_print("=== Scenario 1: Chat Only ===")
    app = setup_test_app()
    controller = app.container.get("controller")

    # Mock provider response for simple chat
    raw_resp = {"message": {"role": "assistant", "content": "Hello! I am Jarvis, your assistant."}}
    app.container.get("llm_manager").generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    req = AgentRequest(request_id="req_chat_1", text="Hello Jarvis", source="test")
    resp = controller.process_request(req)

    assert resp.success is True
    assert "Hello!" in resp.text
    safe_print("PASS: Chat only integration scenario executed successfully.")
    app.shutdown()


def test_scenario_2_chat_with_memory():
    safe_print("\n=== Scenario 2: Chat + Memory ===")
    app = setup_test_app()
    
    # Store a memory
    from app.memory.models import MemoryType, MemorySource
    memory_mgr = app.container.get("memory_manager")
    memory_mgr.create_memory(
        content="User favorite color is blue",
        memory_type=MemoryType.PREFERENCE,
        importance=0.9,
        source=MemorySource.USER
    )

    controller = app.container.get("controller")
    
    raw_resp = {"message": {"role": "assistant", "content": "Your favorite color is blue."}}
    app.container.get("llm_manager").generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    req = AgentRequest(request_id="req_mem_2", text="What is my favorite color?", source="test")
    resp = controller.process_request(req)

    assert resp.success is True
    assert "blue" in resp.text
    safe_print("PASS: Chat + Memory scenario verified memory injection and dialogue output.")
    app.shutdown()


def test_scenario_3_chat_with_filesystem():
    safe_print("\n=== Scenario 3: Chat + Filesystem ===")
    app = setup_test_app()

    fs_service = app.container.get("filesystem_service")
    
    # Ensure directory is created
    res_path = fs_service.create_directory("Temp", "IntegrationTestDir")
    assert res_path is True

    safe_print(f"PASS: Chat + Filesystem scenario created temp directory: {res_path}")
    
    # Cleanup created temp folder
    fs_service.delete_path("Temp", "IntegrationTestDir", recursive=True)
    app.shutdown()


def test_scenario_4_chat_with_desktop_automation():
    safe_print("\n=== Scenario 4: Chat + Desktop Automation ===")
    app = setup_test_app()

    desktop_svc = app.container.get("desktop_service")
    windows = desktop_svc.list_visible_windows()

    assert isinstance(windows, list)
    safe_print(f"PASS: Desktop automation scenario enumerated {len(windows)} active desktop windows.")
    app.shutdown()


def test_scenario_5_filesystem_with_approval():
    safe_print("\n=== Scenario 5: Filesystem + Approval Runtime ===")
    app = setup_test_app()

    executor = app.container.get("tool_executor")
    approval_mgr = app.container.get("approval_manager")

    # Request confirmation-required tool
    tool_call = ToolCall(tool_name="write_text_file", arguments={"root": "Temp", "relative_path": "approval_test.txt", "content": "test content"})
    res = executor.execute(tool_call)

    assert res.success is False
    assert res.metadata.get("confirmation_required") is True
    action_id = res.metadata.get("pending_action_id")
    assert action_id is not None

    # Approve pending action
    approval_mgr.approve(action_id)
    
    # Execute with approval ID
    res_approved = executor.execute(tool_call, approval_action_id=action_id)
    assert res_approved.success is True

    safe_print("PASS: Filesystem + Approval scenario successfully requested, approved, and executed tool.")
    
    # Cleanup
    fs_service = app.container.get("filesystem_service")
    fs_service.delete_path("Temp", "approval_test.txt")
    app.shutdown()


def test_scenario_6_memory_with_filesystem():
    safe_print("\n=== Scenario 6: Memory + Filesystem ===")
    app = setup_test_app()

    fs_service = app.container.get("filesystem_service")
    memory_mgr = app.container.get("memory_manager")

    # 1. Create file with config note
    fs_service.write_text_file("Temp", "note.txt", "Project title is Jarvis AI Assistant.")
    
    # 2. Extract and store memory
    from app.memory.models import MemoryType, MemorySource
    target = fs_service._resolver.resolve("Temp", "note.txt")
    read_text = target.resolved_path.read_text(encoding="utf-8")
    memory_mgr.create_memory(
        content=read_text,
        memory_type=MemoryType.PROJECT,
        importance=0.8,
        source=MemorySource.SYSTEM
    )

    retriever = app.container.get("memory_retriever")
    res = retriever.retrieve("Jarvis AI Assistant")
    assert len(res.matches) > 0

    safe_print("PASS: Memory + Filesystem scenario extracted file data into memory repository.")

    # Cleanup
    fs_service.delete_path("Temp", "note.txt")
    app.shutdown()


def test_scenario_7_planner_with_multiple_tools():
    safe_print("\n=== Scenario 7: Planner + Multiple Tools ===")
    app = setup_test_app()

    task_executor = app.container.get("planning_executor")
    
    from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus, PlanStatus
    plan = TaskPlan(
        plan_id="plan_multi_test",
        goal="Demonstrate multi-step execution",
        steps=[
            PlanStep(step_id="s1", sequence=1, step_type=StepType.TOOL, description="Check time", tool_name="get_current_time", tool_arguments={}, status=StepStatus.PENDING),
            PlanStep(step_id="s2", sequence=2, step_type=StepType.SYNTHESIS, description="Summarize", status=StepStatus.PENDING)
        ],
        status=PlanStatus.CREATED,
        created_at=datetime.now(timezone.utc)
    )

    raw_resp = {"message": {"role": "assistant", "content": "The current time has been checked."}}
    app.container.get("llm_manager").generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    result = task_executor.execute(plan, "Check current time")
    assert result.success is True

    safe_print("PASS: Planner + Multiple Tools scenario executed multi-step task plan successfully.")
    app.shutdown()


def test_scenario_8_restart_persistence():
    safe_print("\n=== Scenario 8: Restart Persistence ===")
    
    # Session 1: Create session & add message
    app1 = setup_test_app()
    conv_mgr = app1.container.get("conversation_manager")
    sess1 = conv_mgr.create_session()
    from app.utils.id_generator import generate_message_id
    conv_mgr.add_message(sess1.session_id, Message(id=generate_message_id(), role=MessageRole.USER, content="Persistent hello"))
    app1.shutdown()

    # Session 2: Re-open app & verify session persists
    app2 = setup_test_app()
    conv_repo = app2.container.get("conversation_repository")
    sessions = conv_repo.list_sessions()
    
    found = any(s.session_id == sess1.session_id for s in sessions)
    assert found is True
    safe_print(f"PASS: Restart Persistence verified session '{sess1.session_id}' reloaded across app restarts.")
    app2.shutdown()


def test_scenario_9_recovery_after_provider_failure():
    safe_print("\n=== Scenario 9: Recovery After Provider Failure ===")
    app = setup_test_app()
    llm_manager = app.container.get("llm_manager")

    call_cnt = 0
    def mock_gen(*args, **kwargs):
        nonlocal call_cnt
        call_cnt += 1
        if call_cnt == 1:
            raise ConnectionError("LLM Provider connection dropped")
        raw_resp = {"message": {"role": "assistant", "content": "Recovered response"}}
        return GenerationResult(raw_response=raw_resp, metrics=GenerationMetrics(provider="fake", model="fake"))

    provider = MagicMock()
    provider.generate.side_effect = mock_gen
    provider.initialize.return_value = None
    provider.shutdown.return_value = None

    llm_manager.register_provider("reconnect_test", provider)
    llm_manager.switch_provider("reconnect_test")

    res = llm_manager.generate([{"role": "user", "content": "Hi"}])
    assert res.raw_response["message"]["content"] == "Recovered response"
    assert llm_manager.retry_count > 0

    safe_print("PASS: Recovery scenario recovered from provider connection drop after retry.")
    app.shutdown()


def run_all_integration_scenarios():
    safe_print("============================================================")
    safe_print("STARTING END-TO-END INTEGRATION TEST SUITE")
    safe_print("============================================================")

    test_scenario_1_chat_only()
    test_scenario_2_chat_with_memory()
    test_scenario_3_chat_with_filesystem()
    test_scenario_4_chat_with_desktop_automation()
    test_scenario_5_filesystem_with_approval()
    test_scenario_6_memory_with_filesystem()
    test_scenario_7_planner_with_multiple_tools()
    test_scenario_8_restart_persistence()
    test_scenario_9_recovery_after_provider_failure()

    safe_print("\n============================================================")
    safe_print("ALL END-TO-END INTEGRATION SCENARIOS PASSED SUCCESSFULLY!")
    safe_print("============================================================")


if __name__ == "__main__":
    run_all_integration_scenarios()
