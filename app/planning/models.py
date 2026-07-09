"""Domain models for task planning and step execution."""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List
from app.core.exceptions import PlanValidationError


class ExecutionMode(Enum):
    """Execution mode chosen for processing a user request."""

    DIRECT = "direct"
    PLANNED = "planned"


class StepType(Enum):
    """The computation style of an individual plan step."""

    TOOL = "TOOL"
    REASONING = "REASONING"
    SYNTHESIS = "SYNTHESIS"


class StepStatus(Enum):
    """Execution progress of an individual plan step."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WAITING_APPROVAL = "WAITING_APPROVAL"


class PlanStatus(Enum):
    """Progress status of a multi-step task plan."""

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    WAITING_APPROVAL = "WAITING_APPROVAL"


@dataclass(frozen=True)
class PlanningDecision:
    """Routing decision determining whether to run request directly or via planning."""

    mode: ExecutionMode
    confidence: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validates decision attributes."""
        if not isinstance(self.mode, ExecutionMode):
            raise PlanValidationError(f"Invalid execution mode: {self.mode}")
        if not (0.0 <= self.confidence <= 1.0):
            raise PlanValidationError(f"Confidence score must be between 0.0 and 1.0, got: {self.confidence}")
        if not self.reason or not self.reason.strip():
            raise PlanValidationError("Routing decision reason must not be empty.")
        # Defensive copy of metadata
        object.__setattr__(self, "metadata", deepcopy(self.metadata))


@dataclass
class PlanStep:
    """A single executable step within a task plan."""

    step_id: str
    sequence: int
    description: str
    step_type: StepType
    tool_name: str | None = None
    tool_arguments: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validates step properties."""
        if not self.step_id or not self.step_id.strip():
            raise PlanValidationError("Step ID must not be empty.")
        if self.sequence <= 0:
            raise PlanValidationError(f"Sequence number must be a positive integer, got: {self.sequence}")
        if not self.description or not self.description.strip():
            raise PlanValidationError("Step description must not be empty.")
        if not isinstance(self.step_type, StepType):
            raise PlanValidationError(f"Invalid step type: {self.step_type}")
        if not isinstance(self.status, StepStatus):
            raise PlanValidationError(f"Invalid step status: {self.status}")
        
        # Enforce consistency of tool_name based on StepType
        if self.step_type == StepType.TOOL:
            if not self.tool_name or not self.tool_name.strip():
                raise PlanValidationError("TOOL step type must specify a tool_name.")
        else:
            if self.tool_name is not None:
                raise PlanValidationError(f"Step type {self.step_type.name} must not specify a tool_name.")

        self.tool_arguments = deepcopy(self.tool_arguments)
        self.metadata = deepcopy(self.metadata)


@dataclass
class TaskPlan:
    """An ordered plan formulated to achieve a user's multi-step goal."""

    plan_id: str
    goal: str
    steps: List[PlanStep]
    status: PlanStatus = PlanStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validates task plan constraints."""
        if not self.plan_id or not self.plan_id.strip():
            raise PlanValidationError("Plan ID must not be empty.")
        if not self.goal or not self.goal.strip():
            raise PlanValidationError("Plan goal must not be empty.")
        if not isinstance(self.status, PlanStatus):
            raise PlanValidationError(f"Invalid plan status: {self.status}")
        if self.created_at.tzinfo is None:
            raise PlanValidationError("Plan created_at must be a timezone-aware datetime.")
        
        # Defensive copy of steps list and metadata
        self.steps = list(self.steps)
        self.metadata = deepcopy(self.metadata)


@dataclass(frozen=True)
class StepObservation:
    """Intermediate execution result context gathered from running a single step."""

    step_id: str
    step_sequence: int
    step_type: StepType
    success: bool
    content: str
    tool_name: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validates observation fields."""
        if not self.step_id or not self.step_id.strip():
            raise PlanValidationError("Observation step_id must not be empty.")
        if self.step_sequence <= 0:
            raise PlanValidationError("Observation step_sequence must be positive.")
        if not isinstance(self.step_type, StepType):
            raise PlanValidationError(f"Invalid observation step type: {self.step_type}")
        if self.created_at.tzinfo is None:
            raise PlanValidationError("Observation created_at must be a timezone-aware datetime.")
        
        object.__setattr__(self, "metadata", deepcopy(self.metadata))


# We will import PlanningMetrics here from app.planning.metrics to keep imports and dependencies clean.
# However, to avoid circular dependencies, PlanExecutionResult takes metrics as Any or PlanningMetrics.
@dataclass(frozen=True)
class PlanExecutionResult:
    """The aggregate final outcome of running a TaskPlan."""

    plan_id: str
    success: bool
    final_response: str
    plan_status: PlanStatus
    steps_total: int
    steps_completed: int
    steps_failed: int
    observations: List[StepObservation]
    metrics: Any  # PlanningMetrics instance
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validates the execution result fields."""
        if not self.plan_id or not self.plan_id.strip():
            raise PlanValidationError("Plan ID must not be empty.")
        if not isinstance(self.plan_status, PlanStatus):
            raise PlanValidationError(f"Invalid plan status: {self.plan_status}")
        
        object.__setattr__(self, "observations", list(self.observations))
        object.__setattr__(self, "metadata", deepcopy(self.metadata))
