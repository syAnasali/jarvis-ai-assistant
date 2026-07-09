"""Diagnostic script for LLMTaskPlanner using local Ollama if available."""

import sys
import json
from app.core.application import Application
from app.core.exceptions import LLMError
from app.agent.models import AgentRequest
from app.planning.planner import LLMTaskPlanner
from app.planning.validator import PlanValidator

def run_diagnostic():
    print("=== Ollama Task Planner Integration Test ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"Application initialization failed: {e}")
        sys.exit(1)

    container = app.container
    llm_manager = container.get("llm_manager")
    registry = container.get("tool_registry")
    
    planner = LLMTaskPlanner(llm_manager)
    validator = PlanValidator(registry)

    prompt = "Check my computer information and current local time, then summarize my environment."
    req = AgentRequest("diag_req_1", prompt, "terminal")
    available_tools = registry.get_schemas()
    
    print(f"Request: {prompt!r}")
    print("Generating plan via Ollama qwen3:8b...")
    
    try:
        plan = planner.create_plan(
            request=req,
            available_tools=available_tools,
            conversation_history=[]
        )
        print(f"\nPlan Formulated Successfully! ID={plan.plan_id}")
        print(f"Goal: {plan.goal!r}")
        print(f"Steps ({len(plan.steps)}):")
        for step in plan.steps:
            print(
                f"  Step {step.sequence}: ID={step.step_id}\n"
                f"    Type: {step.step_type.name}\n"
                f"    Description: {step.description!r}\n"
                f"    Tool: {step.tool_name}\n"
                f"    Arguments: {step.tool_arguments}\n"
            )
            
        print("Validating formulated plan...")
        validator.validate(plan)
        print("Plan validation successful!")
        
    except LLMError as le:
        print(f"\n[WARNING] Ollama execution failed: {le}.")
        print("If Ollama is not running, start it using 'ollama run qwen3:8b' and rerun this script.")
    except Exception as e:
        print(f"\nFAILED: Plan formulation failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
