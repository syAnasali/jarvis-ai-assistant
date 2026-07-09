"""Diagnostic script for planned execution against Ollama."""

import sys
from app.core.application import Application
from app.core.exceptions import LLMError
from app.agent.models import AgentRequest

def run_diagnostic():
    print("=== Planned Execution Integration Test ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"Application initialization failed: {e}")
        sys.exit(1)

    container = app.container
    controller = container.get("controller")

    prompt = "Check the time and system information, compare the findings, and give me a short report."
    req = AgentRequest("planned_exec_req", prompt, "terminal")
    
    print(f"Request: {prompt!r}")
    print("Processing request via AgentController...")
    
    try:
        response = controller.process_request(req)
        print("\nResponse Received Successfully!")
        print(f"Response Text:\n{response.text}")
        print(f"\nResponse Metadata: {response.metadata}")
        
        # Verify plan metrics
        assert response.metadata["execution_mode"] == "planned"
        assert response.metadata["plan_steps"] == 3 or response.metadata["plan_steps"] == 4
        print("\nPlanned execution verification successful!")
        
    except LLMError as le:
        print(f"\n[WARNING] Ollama execution failed: {le}.")
        print("If Ollama is not running, start it using 'ollama run qwen3:8b' and rerun this script.")
    except Exception as e:
        print(f"\nFAILED: Planned execution failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
