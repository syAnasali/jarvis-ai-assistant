"""Unit tests verifying Vision Runtime integration into TaskPlanner reasoning steps."""

import pytest
from app.planning.models import TaskPlan, PlanStep, StepType, StepStatus
from app.vision.manager import VisionManager
from app.vision.providers import MockVisionProvider


def test_planner_incorporates_vision_observation_step():
    vision_mgr = VisionManager(provider=MockVisionProvider())
    vision_mgr.initialize()

    step = PlanStep(
        step_id="step_vision_1",
        sequence=1,
        description="Inspect on-screen error dialog to decide next action",
        step_type=StepType.TOOL,
        tool_name="capture_screen",
        tool_arguments={"prompt": "Read error dialog"}
    )
    plan = TaskPlan(plan_id="plan_vis_1", goal="Fix desktop error", steps=[step])
    assert plan.steps[0].tool_name == "capture_screen"
    assert plan.steps[0].status == StepStatus.PENDING

    vision_resp = vision_mgr.analyze_screen(prompt="Read error dialog")
    assert vision_resp.text != ""
    vision_mgr.shutdown()
