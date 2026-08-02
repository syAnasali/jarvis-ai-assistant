#!/usr/bin/env python3
"""Diagnostics script to verify Runtime Reliability and Recovery.

Runs simulated failure test cases and prints recovery paths and logs.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

try:
    from app.core.application import Application
    from app.agent.models import AgentRequest
    print("Dependencies loaded successfully.")
except ImportError as e:
    print(f"Failed to load dependencies: {e}")
    sys.exit(1)


def run_diagnostics():
    print("=" * 60)
    print("Running Runtime Reliability & Error Recovery Diagnostics")
    print("=" * 60)

    # Initialize Application container
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
        print("Application container initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Application: {e}")
        return

    controller = app.container.get("controller")
    if not controller:
        print("AgentController not found in container.")
        app.shutdown()
        sys.exit(1)

    scenarios = [
        {
            "name": "Provider Shutdown / Ollama Connection Error",
            "prompt": "Say hello to the user",
            "mock_patch": patch("app.ai.manager.LLMManager.generate", side_effect=Exception("Ollama connection failed: ConnectError")),
            "expected_recovery": "ollama_connection_fallback"
        },
        {
            "name": "Permission Denied filesystem error",
            "prompt": "Modify system files",
            "mock_patch": patch("app.agent.controller.AgentController._prepare_request", side_effect=PermissionError("WinError 5: Access is denied")),
            "expected_recovery": "permission_denied_fallback"
        },
        {
            "name": "Missing File / Nonexistent Directory",
            "prompt": "Read file desktop/missing_file.txt",
            "mock_patch": patch("app.agent.controller.AgentController._prepare_request", side_effect=FileNotFoundError("WinError 2: The system cannot find the file specified")),
            "expected_recovery": "file_not_found_fallback"
        },
        {
            "name": "Rejected Approvals",
            "prompt": "Delete document",
            "mock_patch": patch("app.agent.controller.AgentController._prepare_request", side_effect=Exception("Action was rejected by user")),
            "expected_recovery": "rejected_approval_fallback"
        },
        {
            "name": "Timeout limit exceeded",
            "prompt": "Run long task",
            "mock_patch": patch("app.agent.controller.AgentController._prepare_request", side_effect=TimeoutError("The operation timed out")),
            "expected_recovery": "timeout_fallback"
        }
    ]

    passed = 0
    total = len(scenarios)

    for i, tc in enumerate(scenarios, 1):
        print(f"\nScenario {i}: {tc['name']}")
        print(f"Prompt: \"{tc['prompt']}\"")
        
        request = AgentRequest(
            request_id=f"recovery_case_{i}",
            text=tc["prompt"],
            source="diagnostics",
            timestamp=datetime.now(timezone.utc)
        )

        with tc["mock_patch"]:
            response = controller.process_request(request)
            
            print(f"Friendly response: \"{response.text}\"")
            recovery_path = response.metadata.get("recovery_path", "none")
            print(f"Selected Recovery Path: '{recovery_path}'")
            
            if recovery_path == tc["expected_recovery"]:
                print("Result: PASS")
                passed += 1
            else:
                print(f"Result: FAIL (Expected recovery '{tc['expected_recovery']}', got '{recovery_path}')")

    print("\n" + "=" * 60)
    print(f"Recovery Diagnostics completed: {passed}/{total} passed.")
    print("=" * 60)

    app.shutdown()


if __name__ == "__main__":
    run_diagnostics()
