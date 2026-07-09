"""Diagnostic script for testing plan execution failure recovery."""

import sys
from app.core.application import Application
from app.core.exceptions import LLMError
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult
from app.agent.models import AgentRequest

class TempConfirmTool(BaseTool):
    @property
    def name(self) -> str:
        return "temp_restricted_tool"
        
    @property
    def description(self) -> str:
        return "A restricted tool that should block execution."
        
    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.RESTRICTED
        
    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
        
    def execute(self, **kwargs) -> str:
        return "blocked"

def run_diagnostic():
    print("=== Plan Execution Failure Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"Application initialization failed: {e}")
        sys.exit(1)

    container = app.container
    registry = container.get("tool_registry")
    
    # Register the restricted tool
    confirm_tool = TempConfirmTool()
    registry.register(confirm_tool)
    print(f"Registered temporary restricted tool: '{confirm_tool.name}'")

    controller = container.get("controller")

    prompt = "Check the time and run the temporary restricted tool, then give me a short report."
    req = AgentRequest("planning_failure_req", prompt, "terminal")
    
    print(f"Request: {prompt!r}")
    print("Processing request via AgentController...")
    
    try:
        response = controller.process_request(req)
        print("\nResponse Received Successfully!")
        print(f"Response Text:\n{response.text}")
        print(f"\nResponse Metadata: {response.metadata}")
        
        # Verify failure tracking in response
        assert response.success is False
        assert response.metadata["execution_mode"] == "planned"
        assert response.metadata["steps_failed"] >= 1
        print("\nPlan failure recovery diagnostic successful!")
        
    except LLMError as le:
        print(f"\n[WARNING] Ollama execution failed: {le}.")
        print("If Ollama is not running, start it using 'ollama run qwen3:8b' and rerun this script.")
    except Exception as e:
        print(f"\nFAILED: Plan failure diagnostic failed with exception: {e}")
        sys.exit(1)
    finally:
        # Cleanup registered tool
        try:
            registry.remove(confirm_tool.name)
        except Exception:
            pass

if __name__ == "__main__":
    run_diagnostic()
