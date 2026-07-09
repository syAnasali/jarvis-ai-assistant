"""Planner response parser implementation."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from app.core.exceptions import PlanningParseError
from app.planning.models import PlanStep, TaskPlan, StepType, StepStatus, PlanStatus
from app.utils.id_generator import generate_plan_id, generate_step_id


class PlanParser:
    """Parses and structures task plans from raw planner output."""

    def parse_plan(self, raw_output: str) -> TaskPlan:
        """Parses a raw JSON string into a structured TaskPlan domain object.

        Args:
            raw_output: The raw text response from the language model.

        Returns:
            TaskPlan: The validated and structured task plan.

        Raises:
            PlanningParseError: If the output is not valid JSON or doesn't match the schema.
        """
        if not raw_output or not raw_output.strip():
            raise PlanningParseError("Planner output is empty.")

        # Clean markdown code fences if present
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            # Find the start of the JSON object
            first_brace = cleaned.find("{")
            last_brace = cleaned.rfind("}")
            if first_brace != -1 and last_brace != -1:
                cleaned = cleaned[first_brace:last_brace + 1]
            else:
                # Remove first and last lines
                lines = cleaned.splitlines()
                if len(lines) > 2:
                    cleaned = "\n".join(lines[1:-1]).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise PlanningParseError(f"Failed to decode planner response as JSON: {e}") from e

        if not isinstance(data, dict):
            raise PlanningParseError("Planner response must be a JSON object.")

        goal = data.get("goal")
        if not goal or not isinstance(goal, str) or not goal.strip():
            raise PlanningParseError("Planner response is missing a valid 'goal' string.")

        steps_data = data.get("steps")
        if steps_data is None:
            raise PlanningParseError("Planner response is missing 'steps' field.")
        if not isinstance(steps_data, list):
            raise PlanningParseError("'steps' must be a JSON list.")
        if not steps_data:
            raise PlanningParseError("'steps' list must contain at least one step.")

        parsed_steps: List[PlanStep] = []
        for idx, step_data in enumerate(steps_data):
            if not isinstance(step_data, dict):
                raise PlanningParseError(f"Step at index {idx} is not a JSON object.")

            # Validate sequence
            seq_val = step_data.get("sequence")
            if seq_val is None:
                raise PlanningParseError(f"Step at index {idx} is missing 'sequence' number.")
            try:
                sequence = int(seq_val)
            except (ValueError, TypeError) as e:
                raise PlanningParseError(f"Step at index {idx} has invalid sequence type: {seq_val}") from e

            # Validate description
            description = step_data.get("description")
            if not description or not isinstance(description, str) or not description.strip():
                raise PlanningParseError(f"Step at index {idx} has missing or empty description.")

            # Validate type
            type_str = step_data.get("type")
            if not type_str or not isinstance(type_str, str):
                raise PlanningParseError(f"Step at index {idx} has missing or invalid type.")

            try:
                step_type = StepType[type_str.upper()]
            except KeyError:
                raise PlanningParseError(f"Step at index {idx} has unknown type: {type_str}")

            # Validate tool_name
            tool_name = step_data.get("tool_name")
            if tool_name is not None and not isinstance(tool_name, str):
                raise PlanningParseError(f"Step at index {idx} has invalid tool_name type.")

            # Validate arguments
            arguments = step_data.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                raise PlanningParseError(f"Step at index {idx} has invalid arguments format; must be a JSON object.")

            try:
                step = PlanStep(
                    step_id=generate_step_id(),
                    sequence=sequence,
                    description=description,
                    step_type=step_type,
                    tool_name=tool_name,
                    tool_arguments=arguments,
                    status=StepStatus.PENDING,
                    metadata={}
                )
                parsed_steps.append(step)
            except Exception as e:
                raise PlanningParseError(f"Failed to instantiate PlanStep for step {sequence}: {e}") from e

        # Check if a SYNTHESIS step exists in the parsed steps.
        # If not, automatically append a synthesis step at the end to ensure plan validity.
        has_synthesis = any(step.step_type == StepType.SYNTHESIS for step in parsed_steps)
        if not has_synthesis:
            next_seq = max((step.sequence for step in parsed_steps), default=0) + 1
            synthesis_step = PlanStep(
                step_id=generate_step_id(),
                sequence=next_seq,
                description="Synthesize final response",
                step_type=StepType.SYNTHESIS,
                tool_name=None,
                tool_arguments={},
                status=StepStatus.PENDING,
                metadata={}
            )
            parsed_steps.append(synthesis_step)

        try:
            return TaskPlan(
                plan_id=generate_plan_id(),
                goal=goal,
                steps=parsed_steps,
                status=PlanStatus.CREATED,
                created_at=datetime.now(timezone.utc),
                metadata={}
            )
        except Exception as e:
            raise PlanningParseError(f"Failed to instantiate TaskPlan: {e}") from e
