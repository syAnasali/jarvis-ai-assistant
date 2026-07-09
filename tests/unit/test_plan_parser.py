"""Unit tests for PlanParser."""

import pytest
from app.core.exceptions import PlanningParseError
from app.planning.models import PlanStatus, StepStatus, StepType
from app.planning.parser import PlanParser


@pytest.fixture
def parser() -> PlanParser:
    """Fixture returning a PlanParser instance."""
    return PlanParser()


def test_parser_valid_plan(parser):
    """Verify parsing a valid planner JSON payload."""
    payload = """
    {
      "goal": "Decompose system tasks",
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
          "description": "Analyze observations",
          "type": "REASONING",
          "tool_name": null,
          "arguments": {}
        },
        {
          "sequence": 3,
          "description": "Synthesize response",
          "type": "SYNTHESIS",
          "tool_name": null,
          "arguments": {}
        }
      ]
    }
    """
    plan = parser.parse_plan(payload)
    assert plan.plan_id.startswith("plan_")
    assert plan.goal == "Decompose system tasks"
    assert plan.status == PlanStatus.CREATED
    assert len(plan.steps) == 3

    # Step 1
    s1 = plan.steps[0]
    assert s1.step_id.startswith("step_")
    assert s1.sequence == 1
    assert s1.description == "Fetch current local time"
    assert s1.step_type == StepType.TOOL
    assert s1.tool_name == "get_current_time"
    assert s1.tool_arguments == {}
    assert s1.status == StepStatus.PENDING

    # Step 2
    s2 = plan.steps[1]
    assert s2.step_id.startswith("step_")
    assert s2.sequence == 2
    assert s2.description == "Analyze observations"
    assert s2.step_type == StepType.REASONING
    assert s2.tool_name is None
    assert s2.status == StepStatus.PENDING

    # Step 3
    s3 = plan.steps[2]
    assert s3.step_id.startswith("step_")
    assert s3.sequence == 3
    assert s3.description == "Synthesize response"
    assert s3.step_type == StepType.SYNTHESIS
    assert s3.tool_name is None
    assert s3.status == StepStatus.PENDING

    # Verify step IDs unique
    ids = [s.step_id for s in plan.steps]
    assert len(ids) == len(set(ids))


def test_parser_markdown_code_fences(parser):
    """Verify parsing handles markdown code fences wrapper cleanup."""
    payload = """```json
    {
      "goal": "Decompose system tasks",
      "steps": [
        {
          "sequence": 1,
          "description": "Synthesize response",
          "type": "SYNTHESIS",
          "tool_name": null,
          "arguments": {}
        }
      ]
    }
    ```"""
    plan = parser.parse_plan(payload)
    assert plan.goal == "Decompose system tasks"
    assert len(plan.steps) == 1


def test_parser_empty_or_whitespace_rejections(parser):
    """Verify parser rejects empty or whitespace-only inputs."""
    with pytest.raises(PlanningParseError, match="output is empty"):
        parser.parse_plan("")
    with pytest.raises(PlanningParseError, match="output is empty"):
        parser.parse_plan("   ")


def test_parser_invalid_json_rejections(parser):
    """Verify parser rejects invalid JSON syntax or structures."""
    with pytest.raises(PlanningParseError, match="Failed to decode planner response"):
        parser.parse_plan("{invalid_json}")

    with pytest.raises(PlanningParseError, match="response must be a JSON object"):
        parser.parse_plan("[1, 2, 3]")


def test_parser_missing_or_empty_goal(parser):
    """Verify parser rejects payloads missing a goal or with empty goals."""
    payload_no_goal = '{"steps": []}'
    with pytest.raises(PlanningParseError, match="missing a valid 'goal'"):
        parser.parse_plan(payload_no_goal)

    payload_empty_goal = '{"goal": "   ", "steps": []}'
    with pytest.raises(PlanningParseError, match="missing a valid 'goal'"):
        parser.parse_plan(payload_empty_goal)


def test_parser_missing_or_empty_steps(parser):
    """Verify parser rejects missing, non-list, or empty steps list."""
    payload_no_steps = '{"goal": "run test"}'
    with pytest.raises(PlanningParseError, match="missing 'steps' field"):
        parser.parse_plan(payload_no_steps)

    payload_non_list_steps = '{"goal": "run test", "steps": "not_a_list"}'
    with pytest.raises(PlanningParseError, match="'steps' must be a JSON list"):
        parser.parse_plan(payload_non_list_steps)

    payload_empty_steps = '{"goal": "run test", "steps": []}'
    with pytest.raises(PlanningParseError, match="list must contain at least one step"):
        parser.parse_plan(payload_empty_steps)


def test_parser_invalid_step_types(parser):
    """Verify parser rejects unknown step type values."""
    payload = """
    {
      "goal": "Decompose system tasks",
      "steps": [
        {
          "sequence": 1,
          "description": "Synthesize response",
          "type": "UNKNOWN_TYPE",
          "tool_name": null,
          "arguments": {}
        }
      ]
    }
    """
    with pytest.raises(PlanningParseError, match="unknown type"):
        parser.parse_plan(payload)


def test_parser_invalid_step_arguments(parser):
    """Verify parser rejects non-dictionary arguments in step definitions."""
    payload = """
    {
      "goal": "Decompose system tasks",
      "steps": [
        {
          "sequence": 1,
          "description": "Synthesize response",
          "type": "SYNTHESIS",
          "tool_name": null,
          "arguments": "not_a_dict"
        }
      ]
    }
    """
    with pytest.raises(PlanningParseError, match="invalid arguments format; must be a JSON object"):
        parser.parse_plan(payload)


def test_parser_invalid_sequence_types(parser):
    """Verify parser rejects non-integer sequence values."""
    payload = """
    {
      "goal": "Decompose system tasks",
      "steps": [
        {
          "sequence": "first",
          "description": "Synthesize response",
          "type": "SYNTHESIS",
          "tool_name": null,
          "arguments": {}
        }
      ]
    }
    """
    with pytest.raises(PlanningParseError, match="invalid sequence type"):
        parser.parse_plan(payload)
