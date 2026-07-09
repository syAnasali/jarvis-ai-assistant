"""Diagnostic script for safe local capabilities tools."""

import sys
from app.core.application import Application
from app.agent.models import ToolCall

def run_diagnostic():
    print("=== Local Capabilities Tool Diagnostic ===")
    
    # Initialize Application & subsystems
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    executor = app.container.get("tool_executor")
    failures = 0

    # 1. get_disk_usage
    print("\n1. Testing get_disk_usage...")
    tc1 = ToolCall(tool_name="get_disk_usage", arguments={})
    res1 = executor.execute(tc1)
    if res1.success:
        print(f"  [PASS] Path: {res1.output.get('path')}")
        print(f"         Total: {res1.output.get('total_bytes')} bytes")
        print(f"         Used: {res1.output.get('used_bytes')} bytes")
        print(f"         Free: {res1.output.get('free_bytes')} bytes")
        print(f"         Used %: {res1.output.get('used_percent')}%")
    else:
        print(f"  [FAIL] {res1.error}")
        failures += 1

    # 2. find_running_process (query="ollama")
    print("\n2. Testing find_running_process (query='ollama')...")
    tc2 = ToolCall(tool_name="find_running_process", arguments={"query": "ollama"})
    res2 = executor.execute(tc2)
    if res2.success:
        print(f"  [PASS] Match Count: {res2.output.get('match_count')}")
        for match in res2.output.get("matches", []):
            print(f"         PID: {match.get('pid')}, Name: {match.get('name')}, Path: {match.get('executable_path')}")
    else:
        print(f"  [FAIL] {res2.error}")
        failures += 1

    # 3. find_installed_application (query="Visual Studio Code")
    print("\n3. Testing find_installed_application (query='Visual Studio Code')...")
    tc3 = ToolCall(tool_name="find_installed_application", arguments={"query": "Visual Studio Code"})
    res3 = executor.execute(tc3)
    if res3.success:
        print(f"  [PASS] Match Count: {res3.output.get('match_count')}")
        for match in res3.output.get("matches", []):
            print(f"         Name: {match.get('name')}, Version: {match.get('version')}, Publisher: {match.get('publisher')}")
    else:
        print(f"  [FAIL] {res3.error}")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
