"""Domain models and metrics definitions for the filesystem service."""

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict
import threading


@dataclass(frozen=True)
class FilesystemTarget:
    """Immutable model representing a validated target on the filesystem."""

    root: str
    relative_path: str
    resolved_path: Path
    exists: bool
    entry_type: str  # "FILE", "DIRECTORY", or "MISSING"

    @property
    def metadata(self) -> Dict[str, Any]:
        """Returns model-safe metadata for the target, defensively copied."""
        res = {
            "root": self.root,
            "relative_path": self.relative_path,
            "exists": self.exists,
            "entry_type": self.entry_type,
        }
        return copy.deepcopy(res)


class FilesystemMetrics:
    """Thread-safe collector for filesystem metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.inspection_requests = 0
        self.directory_list_requests = 0
        self.create_requests = 0
        self.write_requests = 0
        self.move_requests = 0
        self.delete_requests = 0
        self.successful_mutations = 0
        self.failed_mutations = 0
        self.policy_rejections = 0

    def increment(self, metric_name: str) -> None:
        """Increments a metric counter in a thread-safe manner."""
        with self._lock:
            if hasattr(self, metric_name):
                setattr(self, metric_name, getattr(self, metric_name) + 1)

    def get_metrics_snapshot(self) -> Dict[str, int]:
        """Returns a snapshot copy of all metrics counters."""
        with self._lock:
            return {
                "inspection_requests": self.inspection_requests,
                "directory_list_requests": self.directory_list_requests,
                "create_requests": self.create_requests,
                "write_requests": self.write_requests,
                "move_requests": self.move_requests,
                "delete_requests": self.delete_requests,
                "successful_mutations": self.successful_mutations,
                "failed_mutations": self.failed_mutations,
                "policy_rejections": self.policy_rejections,
            }
