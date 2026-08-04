"""Immutable domain models and dataclasses for the Hierarchical Planning Engine."""

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Tuple


class PlanStatus(Enum):
    """Lifecycle execution status of a task plan."""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    WAITING_APPROVAL = "WAITING_APPROVAL"


class NodeStatus(Enum):
    """Execution status of an individual DAG node."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ROLLED_BACK = "ROLLED_BACK"


class NodeType(Enum):
    """Semantic computation classification of a DAG node."""
    TOOL = "TOOL"
    VISION = "VISION"
    VOICE = "VOICE"
    MEMORY = "MEMORY"
    CONDITIONAL = "CONDITIONAL"
    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"
    APPROVAL = "APPROVAL"


@dataclass(frozen=True)
class Goal:
    """Represents a high-level user goal objective."""
    objective: str
    goal_id: str = field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:8]}")
    priority: int = 1
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("Goal objective cannot be empty.")
        if self.created_at.tzinfo is None:
            raise ValueError("Goal created_at must be timezone-aware.")
        object.__setattr__(self, "context", MappingProxyType(copy.deepcopy(self.context)))


@dataclass(frozen=True)
class PlanNode:
    """An individual node within a Directed Acyclic Graph (DAG) task plan."""
    node_id: str
    description: str
    node_type: NodeType
    action: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    retry_count: int = 0
    max_retries: int = 3
    verification_action: Optional[str] = None
    rollback_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("PlanNode node_id cannot be empty.")
        if not self.description.strip():
            raise ValueError("PlanNode description cannot be empty.")
        copied_deps = tuple(self.dependencies)
        copied_args = MappingProxyType(copy.deepcopy(self.arguments))
        copied_meta = MappingProxyType(copy.deepcopy(self.metadata))
        object.__setattr__(self, "dependencies", copied_deps)
        object.__setattr__(self, "arguments", copied_args)
        object.__setattr__(self, "metadata", copied_meta)


@dataclass(frozen=True)
class Plan:
    """Represents a Directed Acyclic Graph (DAG) task plan."""
    plan_id: str
    goal: Goal
    nodes: Dict[str, PlanNode]
    status: PlanStatus = PlanStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("Plan plan_id cannot be empty.")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("Plan timestamps must be timezone-aware.")
        copied_nodes = MappingProxyType(dict(self.nodes))
        copied_meta = MappingProxyType(copy.deepcopy(self.metadata))
        object.__setattr__(self, "nodes", copied_nodes)
        object.__setattr__(self, "metadata", copied_meta)


@dataclass(frozen=True)
class ExecutionStep:
    """Log record of a single node's execution attempt."""
    step_id: str
    plan_id: str
    node_id: str
    action: str
    arguments: Dict[str, Any]
    status: NodeStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output: Optional[Any] = None
    error_text: Optional[str] = None


@dataclass(frozen=True)
class VerificationResult:
    """Encapsulates outcome verification results for a completed step."""
    is_verified: bool
    verification_action: str
    checked_output: Optional[Any] = None
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RecoveryAction:
    """Represents a recovery strategy chosen when step verification fails."""
    action_type: str  # 'RETRY', 'ALTERNATIVE_TOOL', 'ROLLBACK', 'USER_PROMPT'
    target_node_id: str
    alternative_action: Optional[str] = None
    alternative_arguments: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True)
class PlanProgress:
    """Calculated execution progress of a plan for UI/CLI consumption."""
    plan_id: str
    total_nodes: int
    completed_nodes: int
    failed_nodes: int
    active_nodes: int
    percentage: float
    progress_bar: str
    status_message: str
