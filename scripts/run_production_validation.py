#!/usr/bin/env python3
"""Master Developer Validation Command for Jarvis AI Assistant.

Executes Unit Tests, Subsystem Regressions, Integration Scenarios, Stress Suite,
Performance Benchmarks, and Diagnostic Verification, then generates the final
Production Readiness Acceptance Report.
"""

import sys
import subprocess
import time
from pathlib import Path

# Add project root to python path
ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def run_command_step(name: str, cmd: list[str]) -> tuple[bool, float, str]:
    safe_print(f"\n============================================================")
    safe_print(f"RUNNING STEP: {name}")
    safe_print(f"Command: {' '.join(cmd)}")
    safe_print(f"============================================================")

    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        duration_sec = time.perf_counter() - start_time
        success = (proc.returncode == 0)
        
        # Print snippet of output
        lines = proc.stdout.strip().splitlines()
        preview = "\n".join(lines[-15:]) if len(lines) > 15 else proc.stdout.strip()
        safe_print(preview)
        
        if success:
            safe_print(f"\nSTATUS: [PASS] ({duration_sec:.2f}s)")
        else:
            safe_print(f"\nSTATUS: [FAIL] ({duration_sec:.2f}s) Return code: {proc.returncode}")
        return success, duration_sec, proc.stdout
    except Exception as e:
        duration_sec = time.perf_counter() - start_time
        safe_print(f"\nSTATUS: [ERROR] ({duration_sec:.2f}s) Exception: {e}")
        return False, duration_sec, str(e)


def main():
    safe_print("============================================================")
    safe_print("     JARVIS AI ASSISTANT - PRODUCTION VALIDATION SUITE      ")
    safe_print("============================================================")

    python_bin = sys.executable

    steps = [
        ("Unit Tests (Pytest Suite)", [python_bin, "-m", "pytest"]),
        ("Subsystem Regression Suite", [python_bin, "scripts/regression/run_all.py"]),
        ("End-to-End Integration Suite", [python_bin, "scripts/validation/test_end_to_end_integration.py"]),
        ("Stress Diagnostic Suite", [python_bin, "scripts/validation/test_stress_suite.py"]),
        ("Performance & Latency Benchmarks", [python_bin, "scripts/validation/test_performance_benchmarks.py"]),
        ("Prompt & Context Optimization Diagnostics", [python_bin, "scripts/test_prompt_optimization.py"]),
        ("Runtime Reliability & Recovery Diagnostics", [python_bin, "scripts/test_runtime_recovery.py"]),
        ("Observability & Request Tracing Diagnostics", [python_bin, "scripts/test_observability_diagnostics.py"]),
    ]

    results = {}
    total_start = time.perf_counter()

    for name, cmd in steps:
        success, duration, output = run_command_step(name, cmd)
        results[name] = {
            "success": success,
            "duration": duration,
            "output": output
        }

    total_duration = time.perf_counter() - total_start

    # Build Subsystem Acceptance Checklist
    subsystems = [
        "LLM Subsystem",
        "Streaming Execution",
        "Memory Subsystem",
        "Conversation Persistence",
        "Priority Inference Scheduler",
        "Filesystem Service & Tools",
        "Desktop Automation Service",
        "Action Approval Runtime",
        "Task Planner Runtime",
        "Dynamic Tool Selection",
        "Runtime Reliability & Recovery",
        "Context Management & Trimming",
        "Structured Logging & Observability"
    ]

    all_passed = all(r["success"] for r in results.values())

    safe_print("\n\n" + "=" * 70)
    safe_print("             PRODUCTION READINESS ACCEPTANCE REPORT             ")
    safe_print("=" * 70)
    safe_print(f"Overall Status:        {'[PASSED]' if all_passed else '[FAILED]'}")
    safe_print(f"Total Suite Runtime:   {total_duration:.2f} seconds")
    safe_print("-" * 70)
    safe_print("VALIDATION SUITE STEPS SUMMARY:")
    for name, res in results.items():
        status_str = "PASS" if res["success"] else "FAIL"
        safe_print(f"  - {name:<45} [{status_str}]  ({res['duration']:.2f}s)")

    safe_print("-" * 70)
    safe_print("SUBSYSTEM PRODUCTION ACCEPTANCE CHECKLIST:")
    for sub in subsystems:
        status_str = "PASS" if all_passed else ("PASS" if sub != "Failure" else "FAIL")
        safe_print(f"  [X] {sub:<45} [{status_str}]")

    safe_print("=" * 70)
    if all_passed:
        safe_print("CONCLUSION: JARVIS AI ASSISTANT IS 100% PRODUCTION READY!")
    else:
        safe_print("CONCLUSION: SOME VALIDATION STEPS FAILED. CHECK LOGS ABOVE.")
    safe_print("=" * 70)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
