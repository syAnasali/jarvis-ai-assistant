"""Manager class coordinating approval workflows and lifecycle actions."""

import copy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from app.core.exceptions import ApprovalError
from app.core.logger import JarvisLogger
from app.approval.models import PendingAction, PendingActionStatus
from app.approval.repository import ApprovalRepository
from app.tools.models import ToolPermission
from app.utils.id_generator import generate_action_id

logger = JarvisLogger.get_logger("approval_manager")


def canonicalize(val: Any) -> Any:
    """Recursively normalizes a JSON-compatible python object for deterministic comparison."""
    if isinstance(val, dict):
        return {k: canonicalize(v) for k, v in sorted(val.items())}
    elif isinstance(val, list):
        return [canonicalize(x) for x in val]
    elif isinstance(val, float):
        # Round floats slightly to prevent precision/representation mismatches
        return round(val, 6)
    return val


class ApprovalManager:
    """Coordinates creating, approving, rejecting, expiring, and consuming approvals."""

    def __init__(self, repository: ApprovalRepository, timeout_seconds: int = 120) -> None:
        """Initializes the ApprovalManager.

        Args:
            repository: The approval repository.
            timeout_seconds: Expiration timeout in seconds.
        """
        self._repository = repository
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = timeout_seconds

    def create_pending_action(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        permission_level: ToolPermission,
        reason: str,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PendingAction:
        """Creates and persists a new PendingAction in PENDING status."""
        action_id = generate_action_id()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._timeout_seconds)

        action = PendingAction(
            action_id=action_id,
            tool_name=tool_name,
            arguments=copy.deepcopy(arguments),
            permission_level=permission_level,
            status=PendingActionStatus.PENDING,
            created_at=now,
            expires_at=expires_at,
            reason=reason,
            request_id=request_id,
            session_id=session_id,
            metadata=copy.deepcopy(metadata or {})
        )

        self._repository.add(action)
        logger.info(f"Pending action created: action_id={action_id} tool_name={tool_name} status=pending")
        return action

    def approve(self, action_id: str) -> None:
        """Approves a pending action."""
        self.expire_pending_actions()
        action = self._repository.get(action_id)
        if not action:
            raise ApprovalError(f"Action '{action_id}' not found.")

        if action.status == PendingActionStatus.EXPIRED:
            raise ApprovalError(f"Cannot approve expired action '{action_id}'.")
        if action.status != PendingActionStatus.PENDING:
            raise ApprovalError(f"Cannot approve action '{action_id}' with status '{action.status.value}'. Only PENDING actions can be approved.")

        self._repository.update_status(action_id, PendingActionStatus.APPROVED)
        logger.info(f"Action approved: action_id={action_id} tool_name={action.tool_name}")

    def reject(self, action_id: str) -> None:
        """Rejects a pending action."""
        self.expire_pending_actions()
        action = self._repository.get(action_id)
        if not action:
            raise ApprovalError(f"Action '{action_id}' not found.")

        if action.status != PendingActionStatus.PENDING:
            raise ApprovalError(f"Cannot reject action '{action_id}' with status '{action.status.value}'. Only PENDING actions can be rejected.")

        self._repository.update_status(action_id, PendingActionStatus.REJECTED)
        logger.info(f"Action rejected: action_id={action_id} tool_name={action.tool_name}")

    def get(self, action_id: str) -> Optional[PendingAction]:
        """Retrieves an action, applying lazy expiration first."""
        self.expire_pending_actions()
        return self._repository.get(action_id)

    def expire_pending_actions(self) -> int:
        """Transitions PENDING actions past expires_at to EXPIRED status."""
        now = datetime.now(timezone.utc)
        count = self._repository.expire_actions(now)
        if count > 0:
            logger.info(f"Expired {count} pending actions past timestamp {now.isoformat()}")
        return count

    def consume_approved_action(self, action_id: str, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validates the exact payload of an approved action and atomically consumes it once.

        Raises:
            ApprovalError: If authorization fails, payload mismatched, or already consumed.
        """
        self.expire_pending_actions()
        action = self._repository.get(action_id)
        if not action:
            raise ApprovalError(f"Action '{action_id}' not found.")

        if action.status == PendingActionStatus.PENDING:
            raise ApprovalError(f"Action '{action_id}' is still PENDING and cannot be executed yet.")
        if action.status == PendingActionStatus.REJECTED:
            raise ApprovalError(f"Action '{action_id}' was REJECTED and cannot be executed.")
        if action.status == PendingActionStatus.EXPIRED:
            raise ApprovalError(f"Action '{action_id}' has EXPIRED and cannot be executed.")
        if action.status == PendingActionStatus.EXECUTED:
            logger.warning(f"Replay blocked: Action '{action_id}' has already been executed.")
            raise ApprovalError(f"Replay blocked: Action '{action_id}' has already been executed.")
        if action.status == PendingActionStatus.FAILED:
            raise ApprovalError(f"Action '{action_id}' has already FAILED and cannot be executed.")
        if action.status != PendingActionStatus.APPROVED:
            raise ApprovalError(f"Action '{action_id}' has invalid status '{action.status.value}'.")

        # Freeze comparison of tool name and arguments
        if action.tool_name != tool_name:
            self._repository.update_status(action_id, PendingActionStatus.FAILED)
            logger.error(f"Payload mismatch (tool_name): expected '{action.tool_name}', got '{tool_name}'")
            raise ApprovalError("Payload mismatch: tool name does not match approved action.")

        if canonicalize(action.arguments) != canonicalize(arguments):
            self._repository.update_status(action_id, PendingActionStatus.FAILED)
            logger.error("Payload mismatch (arguments): arguments do not match approved parameters.")
            raise ApprovalError("Payload mismatch: arguments do not match approved parameters.")

        # Atomically transition APPROVED -> EXECUTED
        success = self._repository.atomic_consume(action_id)
        if not success:
            logger.warning(f"Replay blocked: Concurrent consumption failed for action '{action_id}'.")
            raise ApprovalError(f"Replay blocked: Action '{action_id}' has already been consumed.")

        logger.info(f"Approval consumed successfully: action_id={action_id} tool_name={tool_name}")
