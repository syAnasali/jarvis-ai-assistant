"""Diagnostic script for ExecutionRouter."""

import sys
from app.agent.models import AgentRequest
from app.planning.models import ExecutionMode
from app.planning.router import ExecutionRouter

def run_diagnostic():
    print("=== ExecutionRouter Diagnostic ===")
    router = ExecutionRouter()
    
    test_cases = [
        # DIRECT cases
        ("What time is it?", ExecutionMode.DIRECT),
        ("Tell me about this computer.", ExecutionMode.DIRECT),
        ("Explain photosynthesis.", ExecutionMode.DIRECT),
        ("Respond with exactly OK.", ExecutionMode.DIRECT),
        ("What is my name?", ExecutionMode.DIRECT),
        ("Write a Python function to reverse a string.", ExecutionMode.DIRECT),
        ("Tell me about Python and Java.", ExecutionMode.DIRECT),
        # PLANNED cases
        ("Check my computer information and current local time, then summarize my environment.", ExecutionMode.PLANNED),
        ("Inspect my system, evaluate whether it looks suitable for Jarvis development, and recommend what I should inspect next.", ExecutionMode.PLANNED),
        ("Check the time and system information, compare the findings, and give me a short report.", ExecutionMode.PLANNED),
        ("Gather system details, evaluate them, and recommend next steps.", ExecutionMode.PLANNED),
    ]

    failed = 0
    for idx, (prompt, expected_mode) in enumerate(test_cases):
        req = AgentRequest(f"req_{idx}", prompt, "terminal")
        decision = router.route(req)
        
        status = "PASS" if decision.mode == expected_mode else "FAIL"
        if status == "FAIL":
            failed += 1
        
        print(
            f"Case {idx + 1}: [{status}] Prompt: {prompt!r}\n"
            f"  Expected: {expected_mode.name}, Got: {decision.mode.name}\n"
            f"  Confidence: {decision.confidence:.2f}, Reason: {decision.reason}\n"
            f"  Metadata: {decision.metadata}\n"
        )
        
    print(f"Diagnostic completed: {len(test_cases) - failed}/{len(test_cases)} cases passed.")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
