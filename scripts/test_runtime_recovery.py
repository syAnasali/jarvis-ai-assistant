#!/usr/bin/env python3
"""Diagnostic script to verify Runtime Reliability and Recovery mechanisms."""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.core.application import Application
from app.config.settings import settings
from app.core.exceptions import (
    JarvisError,
    RecoverableError,
    NonRecoverableError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    ToolTimeoutError,
    ToolCancelledError,
)
from app.ai.manager import LLMManager
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import ToolCall
from app.core.diagnostics import DiagnosticsProvider


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


class SlowTool(BaseTool):
    name = "slow_test_tool"
    description = "Test tool that sleeps beyond timeout."
    permission_level = ToolPermission.SAFE

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "sleep_time": {"type": "number", "description": "Sleep duration"}
                }
            }
        }

    def execute(self, sleep_time: float = 2.0) -> str:
        time.sleep(sleep_time)
        return "completed"


def test_provider_recovery_and_retries():
    safe_print("=== 1. Testing LLM Provider Recovery & Retry Policy ===")
    
    failing_provider = MagicMock()
    # Fail first 2 attempts, succeed on 3rd attempt
    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("LLM provider socket closed")
        from app.ai.models import GenerationResult, GenerationMetrics
        raw_resp = {"message": {"role": "assistant", "content": "Recovered response text"}}
        return GenerationResult(
            raw_response=raw_resp,
            metrics=GenerationMetrics(provider="fake", model="fake_model", load_duration_ms=1.0, prompt_eval_duration_ms=1.0, generation_duration_ms=1.0, prompt_tokens=5, generated_tokens=5)
        )

    failing_provider.generate.side_effect = mock_generate
    failing_provider.initialize.return_value = None
    failing_provider.shutdown.return_value = None

    llm_manager = LLMManager()
    llm_manager.register_provider("test_failing", failing_provider)
    llm_manager.switch_provider("test_failing")

    res = llm_manager.generate([{"role": "user", "content": "Hello"}])

    assert res.raw_response["message"]["content"] == "Recovered response text"
    assert llm_manager.retry_count == 2
    assert llm_manager.recovery_success_count == 1
    assert llm_manager.provider_reconnect_count == 2

    safe_print("PASS: Provider retry policy recovered after 2 transient failures.")


def test_tool_timeout_and_cancellation():
    safe_print("\n=== 2. Testing Tool Execution Timeout & Cancellation ===")
    registry = ToolRegistry()
    slow_tool = SlowTool()
    slow_tool.timeout_seconds = 0.1  # Fast timeout for test
    registry.register(slow_tool)

    executor = ToolExecutor(registry)

    # 1. Timeout Test
    tool_call = ToolCall(tool_name="slow_test_tool", arguments={"sleep_time": 0.5})
    res_timeout = executor.execute(tool_call)

    assert res_timeout.success is False
    assert "timed out" in res_timeout.error.lower()
    assert res_timeout.metadata.get("timeout") is True
    assert executor.timeouts_count == 1

    safe_print("PASS: Tool execution timeout caught and reported cleanly.")

    # 2. Cancellation Test
    executor.cancel_execution()
    res_cancel = executor.execute(tool_call)

    assert res_cancel.success is False
    assert "cancelled" in res_cancel.error.lower()
    assert res_cancel.metadata.get("cancelled") is True
    assert executor.cancellations_count == 1

    safe_print("PASS: Tool execution cancellation handled safely.")
    executor.shutdown()


def test_exception_hierarchy():
    safe_print("\n=== 3. Testing Exception Hierarchy Classification ===")
    
    rec_err = ProviderUnavailableError("Provider offline")
    assert isinstance(rec_err, RecoverableError)
    assert isinstance(rec_err, JarvisError)

    non_rec_err = NonRecoverableError("Fatal corruption")
    assert isinstance(non_rec_err, JarvisError)
    assert not isinstance(non_rec_err, RecoverableError)

    t_err = ToolTimeoutError("Timeout exceeded")
    assert isinstance(t_err, RecoverableError)

    safe_print("PASS: Exception hierarchy correctly separates recoverable vs non-recoverable errors.")


def test_subsystem_clean_shutdown():
    safe_print("\n=== 4. Testing Clean Subsystem Shutdown Sequence ===")
    app = Application()
    app.initialize()

    # Trigger orderly shutdown
    app.shutdown()

    from app.core.lifecycle import ApplicationState
    assert app.state == ApplicationState.STOPPED
    safe_print("PASS: All core subsystems shut down cleanly without unhandled exceptions.")


def test_recovery_diagnostics():
    safe_print("\n=== 5. Testing Recovery Diagnostics Provider ===")
    app = Application()
    app.initialize()

    diagnostics = app.get_diagnostics()

    assert "recovery" in diagnostics
    rec_info = diagnostics["recovery"]
    assert "retry_count" in rec_info
    assert "recovery_success" in rec_info
    assert "timeouts" in rec_info
    assert "cancellations" in rec_info
    assert "provider_reconnects" in rec_info

    safe_print("PASS: Recovery diagnostics collected successfully.")
    safe_print(f"Diagnostics Payload: {rec_info}")
    app.shutdown()


def run_all_recovery_tests():
    safe_print("============================================================")
    safe_print("STARTING RUNTIME RELIABILITY & RECOVERY TEST SUITE")
    safe_print("============================================================")

    test_provider_recovery_and_retries()
    test_tool_timeout_and_cancellation()
    test_exception_hierarchy()
    test_subsystem_clean_shutdown()
    test_recovery_diagnostics()

    safe_print("\n============================================================")
    safe_print("ALL RUNTIME RELIABILITY & RECOVERY TESTS PASSED!")
    safe_print("============================================================")


if __name__ == "__main__":
    run_all_recovery_tests()
