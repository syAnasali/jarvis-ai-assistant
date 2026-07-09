"""Diagnostic script for PlanParser and PlanValidator."""

import sys
from app.core.exceptions import PlanningParseError, PlanValidationError
from app.planning.parser import PlanParser
from app.planning.validator import PlanValidator
from app.tools.registry import ToolRegistry
from app.tools.builtin.system import CurrentTimeTool, SystemInfoTool

def run_diagnostic():
    print("=== PlanParser and PlanValidator Diagnostic ===")
    registry = ToolRegistry()
    registry.register(CurrentTimeTool())
    registry.register(SystemInfoTool())

    parser = PlanParser()
    validator = PlanValidator(registry)

    valid_payload = """
    {
      "goal": "Verify system time and parameters",
      "steps": [
        {
          "sequence": 1,
          "description": "Fetch current local time",
          "type": "TOOL",
          "tool_name": "get_current_time",
          "arguments": {}
        },
        {
          "sequence": 2,
          "description": "Fetch basic non-sensitive system info",
          "type": "TOOL",
          "tool_name": "get_system_info",
          "arguments": {}
        },
        {
          "sequence": 3,
          "description": "Analyze findings and compare",
          "type": "REASONING",
          "tool_name": null,
          "arguments": {}
        },
        {
          "sequence": 4,
          "description": "Formulate final report output",
          "type": "SYNTHESIS",
          "tool_name": null,
          "arguments": {}
        }
      ]
    }
    """

    invalid_payload_sequence_gap = """
    {
      "goal": "Test goal",
      "steps": [
        {
          "sequence": 1,
          "description": "Fetch time",
          "type": "TOOL",
          "tool_name": "get_current_time",
          "arguments": {}
        },
        {
          "sequence": 3,
          "description": "Formulate final report",
          "type": "SYNTHESIS",
          "tool_name": null,
          "arguments": {}
        }
      ]
    }
    """

    print("1. Parsing valid payload...")
    try:
        plan = parser.parse_plan(valid_payload)
        print(f"  Successfully parsed TaskPlan: ID={plan.plan_id}, goal={plan.goal!r}, steps={len(plan.steps)}")
        for step in plan.steps:
            print(f"    Step {step.sequence}: ID={step.step_id}, Type={step.step_type.name}, Tool={step.tool_name}")
        
        print("  Validating parsed plan...")
        validator.validate(plan)
        print("  Successfully validated plan.")
    except Exception as e:
        print(f"  FAILED: Unexpected parsing/validation exception: {e}")
        sys.exit(1)

    print("\n2. Parsing invalid payload (sequence gap)...")
    try:
        plan = parser.parse_plan(invalid_payload_sequence_gap)
        print("  Parsed plan. Validating (expecting error)...")
        validator.validate(plan)
        print("  FAILED: Plan with sequence gap was incorrectly marked valid.")
        sys.exit(1)
    except PlanValidationError as pve:
        print(f"  PASSED: Correctly caught validation error: {pve}")
    except Exception as e:
        print(f"  FAILED: Unexpected exception: {e}")
        sys.exit(1)

    print("\nDiagnostic completed successfully.")

if __name__ == "__main__":
    run_diagnostic()
