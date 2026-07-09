"""Diagnostic script for planned local environment execution."""

import sys
from app.core.application import Application
from app.agent.models import AgentRequest

def run_diagnostic():
    print("=== Planned Local Environment Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    controller = app.container.get("controller")
    
    prompt = "Check my disk space and whether Ollama is running, then summarize whether my computer looks ready for local Jarvis development."
    req = AgentRequest("planned_env_req", prompt, "terminal")
    
    print(f"Request: {prompt!r}")
    print("Processing request via AgentController...")
    
    failures = 0
    try:
        res = controller.process_request(req)
        print("\nResponse Received Successfully!")
        print(f"Response Text:\n{res.text}")
        print(f"\nResponse Metadata: {res.metadata}")
        
        # Verify PLANNED routing
        if res.metadata.get("execution_mode") == "planned":
            print("  [PASS] Request correctly routed to PLANNED path.")
        else:
            print(f"  [FAIL] Request routed to DIRECT path instead of PLANNED. Metadata: {res.metadata}")
            failures += 1
            
        # Verify steps completed and tools executed
        steps_completed = res.metadata.get("steps_completed", 0)
        tool_calls = res.metadata.get("tool_calls", 0)
        plan_status = res.metadata.get("plan_status", "UNKNOWN")
        
        print(f"  Steps completed: {steps_completed}")
        print(f"  Tool calls executed: {tool_calls}")
        print(f"  Plan status: {plan_status}")
        
        if steps_completed >= 3:
            print("  [PASS] Plan contains expected steps (disk space check, process check, synthesis).")
        else:
            print(f"  [FAIL] Plan has insufficient steps. Completed: {steps_completed}")
            failures += 1
            
        if tool_calls >= 1:
            print("  [PASS] Plan successfully called local capability tools.")
        else:
            print("  [FAIL] Plan did not execute any local capability tools.")
            failures += 1
            
        if res.text and len(res.text.strip()) > 0:
            print("  [PASS] Final synthesized response is non-empty.")
        else:
            print("  [FAIL] Final response is empty.")
            failures += 1
            
    except Exception as e:
        print(f"  [FAIL] Planned execution failed with exception: {e}")
        failures += 1

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
