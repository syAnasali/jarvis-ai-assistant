"""End-to-end integration validation for confirmation tool approval workflow."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from app.core.application import Application
from app.agent.models import AgentRequest, ToolCall
from app.ai.models import GenerationResult, GenerationMetrics
from app.agent.messages import Message, MessageRole


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def setup_test_app():
    app = Application()
    app.initialize()
    app._initialize_llm()
    app._initialize_agent()
    return app


def test_delete_path_approval_workflow_integration():
    safe_print("\n=== Integration Test 1: delete_path Confirmation Lifecycle ===")
    app = setup_test_app()
    fs_service = app.container.get("filesystem_service")
    approval_mgr = app.container.get("approval_manager")
    controller = app.container.get("controller")
    llm_manager = app.container.get("llm_manager")

    # 1. Create target file
    fs_service.write_text_file("Temp", "integration_delete.txt", "data to delete")

    # 2. Mock model response requesting delete_path
    raw_resp_delete = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "delete_path",
                    "arguments": {"root": "Temp", "relative_path": "integration_delete.txt"}
                }
            }]
        }
    }

    # First turn: Model requests tool call
    llm_manager.generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp_delete,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    req = AgentRequest(request_id="req_del_1", text="Delete integration_delete.txt in Temp", source="test")
    resp1 = controller.process_request(req)

    # Verify response is suspended for confirmation, text is empty (no leaked internal log error)
    assert resp1.success is False
    assert resp1.metadata.get("confirmation_required") is True
    action_id = resp1.metadata.get("pending_action_id")
    assert action_id is not None
    assert "was blocked because it requires confirmation" not in resp1.text
    safe_print("PASS: delete_path suspended execution cleanly without leaking internal error text.")

    # 3. Approve action
    approval_mgr.approve(action_id)

    # Second turn: Resumption with approval ID. Model generates final user confirmation.
    raw_resp_final = {
        "message": {
            "role": "assistant",
            "content": "I have successfully deleted integration_delete.txt from Temp."
        }
    }
    llm_manager.generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp_final,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    resp2 = controller.process_request(req, approval_action_id=action_id)
    assert resp2.success is True
    assert "successfully deleted" in resp2.text.lower()
    safe_print("PASS: Approved execution completed tool and yielded final user-facing text confirmation.")
    app.shutdown()


def test_write_text_file_approval_workflow_integration():
    safe_print("\n=== Integration Test 2: write_text_file Confirmation Lifecycle ===")
    app = setup_test_app()
    fs_service = app.container.get("filesystem_service")
    approval_mgr = app.container.get("approval_manager")
    controller = app.container.get("controller")
    llm_manager = app.container.get("llm_manager")

    raw_resp_write = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "write_text_file",
                    "arguments": {"root": "Temp", "relative_path": "integration_write.txt", "content": "Hello"}
                }
            }]
        }
    }
    llm_manager.generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp_write,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    req = AgentRequest(request_id="req_write_1", text="Write Hello to integration_write.txt in Temp", source="test")
    resp1 = controller.process_request(req)

    assert resp1.success is False
    assert resp1.metadata.get("confirmation_required") is True
    action_id = resp1.metadata.get("pending_action_id")
    assert action_id is not None
    assert "was blocked because it requires confirmation" not in resp1.text
    safe_print("PASS: write_text_file suspended execution cleanly.")

    approval_mgr.approve(action_id)

    raw_resp_final = {
        "message": {
            "role": "assistant",
            "content": "I have created and written content to integration_write.txt."
        }
    }
    llm_manager.generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp_final,
        metrics=GenerationMetrics(provider="ollama", model="qwen2.5:7b")
    ))

    resp2 = controller.process_request(req, approval_action_id=action_id)
    assert resp2.success is True
    assert "written content" in resp2.text.lower()
    safe_print("PASS: write_text_file completed upon approval and yielded final text.")

    # Cleanup
    fs_service.delete_path("Temp", "integration_write.txt")
    app.shutdown()


def run_all_approval_integration_tests():
    safe_print("============================================================")
    safe_print("STARTING APPROVAL WORKFLOW INTEGRATION TEST SUITE")
    safe_print("============================================================")
    test_delete_path_approval_workflow_integration()
    test_write_text_file_approval_workflow_integration()
    safe_print("============================================================")
    safe_print("ALL APPROVAL WORKFLOW INTEGRATION TESTS PASSED SUCCESSFULLY!")
    safe_print("============================================================")


if __name__ == "__main__":
    run_all_approval_integration_tests()
