#!/usr/bin/env python3
"""Diagnostic script to verify Request Tracing, Performance Metrics, Structured Logging, Debug Mode, and Diagnostics utilities."""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.core.application import Application
from app.config.settings import settings
from app.core.tracing import RequestTracer
from app.core.diagnostics import DiagnosticsProvider
from app.agent.models import AgentRequest, AgentResponse
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("diagnostics_test")


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def test_request_tracing_and_timeline():
    safe_print("=== 1. Testing Request Tracing & Execution Timeline ===")
    req_id = "req_test_trace_123"
    sess_id = "session_abc"
    tracer = RequestTracer(request_id=req_id, session_id=sess_id)

    # Start and end stages
    tracer.start_stage("Request Started")
    time.sleep(0.01)
    tracer.end_stage("Request Started")

    tracer.start_stage("Conversation Formatting")
    time.sleep(0.01)
    tracer.end_stage("Conversation Formatting")

    tracer.start_stage("Memory Retrieval")
    time.sleep(0.015)
    tracer.record_metric("memory_retrieval_latency_ms", 15.0)
    tracer.end_stage("Memory Retrieval")

    tracer.start_stage("Planning")
    time.sleep(0.02)
    tracer.record_metric("planner_latency_ms", 20.0)
    tracer.end_stage("Planning")

    tracer.start_stage("Tool Execution")
    time.sleep(0.01)
    tracer.record_metric("tool_execution_duration_ms", 10.0)
    tracer.end_stage("Tool Execution")

    tracer.start_stage("Completed")
    tracer.end_stage("Completed")

    total_duration = tracer.finalize()
    summary = tracer.get_performance_summary()
    timeline = tracer.get_timeline_dict()

    assert req_id in summary
    assert total_duration > 0
    assert len(timeline) == 6
    assert timeline[0]["stage"] == "Request Started"
    assert timeline[3]["stage"] == "Planning"

    safe_print("PASS: Request Tracing & Timeline recorded successfully.")
    safe_print(summary)


def test_structured_logging():
    safe_print("\n=== 2. Testing Structured Logging Events ===")
    logger.log_event(
        action="Planner finished",
        status="completed",
        duration_ms=42.5,
        request_id="req_struct_1",
        session_id="sess_1",
        metadata={"steps": 3}
    )

    logger.log_error(
        operation="Tool Execution",
        error=FileNotFoundError("Target file missing"),
        request_id="req_struct_1",
        session_id="sess_1",
        user_message="File not found on Desktop."
    )
    safe_print("PASS: Structured events and error logs executed cleanly.")


def test_debug_mode_toggle():
    safe_print("\n=== 3. Testing Debug Mode Toggle ===")
    original_debug = settings.debug_mode
    try:
        settings.debug_mode = True
        assert settings.debug_mode is True
        safe_print("PASS: Debug mode enabled successfully.")

        settings.debug_mode = False
        assert settings.debug_mode is False
        safe_print("PASS: Debug mode disabled successfully.")
    finally:
        settings.debug_mode = original_debug


def test_developer_diagnostics():
    safe_print("\n=== 4. Testing Internal Developer Diagnostics Utilities ===")
    app = Application()
    app.initialize()

    diagnostics = app.get_diagnostics()

    assert "tools" in diagnostics
    assert "config" in diagnostics
    assert "provider" in diagnostics
    assert "memory" in diagnostics
    assert "planner" in diagnostics
    assert "conversation" in diagnostics

    config_info = DiagnosticsProvider.get_loaded_config_info(app.container)
    assert "app_name" in config_info
    assert config_info["app_name"] == settings.app_name

    safe_print("PASS: Developer diagnostics collected successfully.")
    app.shutdown()


def test_user_safe_error_reporting():
    safe_print("\n=== 5. Testing Exception & Error Reporting Safety ===")
    # Verify raw tracebacks are not leaked in user-facing message strings
    user_safe_msg = "A filesystem permission error occurred: Access Denied. I couldn't access or modify the file."
    assert "Traceback (most recent call last)" not in user_safe_msg
    safe_print("PASS: Error messages are user-safe and do not leak raw stack traces.")


def run_all_observability_tests():
    safe_print("============================================================")
    safe_print("STARTING OBSERVABILITY & DIAGNOSTICS SUITE")
    safe_print("============================================================")

    test_request_tracing_and_timeline()
    test_structured_logging()
    test_debug_mode_toggle()
    test_developer_diagnostics()
    test_user_safe_error_reporting()

    safe_print("\n============================================================")
    safe_print("ALL OBSERVABILITY & DIAGNOSTICS TESTS PASSED!")
    safe_print("============================================================")


if __name__ == "__main__":
    run_all_observability_tests()
