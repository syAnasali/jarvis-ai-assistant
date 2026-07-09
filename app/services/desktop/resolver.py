"""Window resolver mapping human references to visible DesktopWindows."""

from typing import List, Optional
from app.services.desktop.models import DesktopWindow


class ResolutionStatus:
    RESOLVED = "RESOLVED"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"


class ResolutionResult:
    """Encapsulates the output of a window resolution request."""

    def __init__(
        self,
        status: str,
        window: Optional[DesktopWindow] = None,
        candidates: Optional[List[DesktopWindow]] = None,
    ) -> None:
        self.status = status
        self.window = window
        self.candidates = candidates or []

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "window": {
                "window_id": self.window.window_id,
                "title": self.window.title,
                "process_name": self.window.process_name,
            } if self.window else None,
            "candidates": [
                {
                    "window_id": c.window_id,
                    "title": c.title,
                    "process_name": c.process_name,
                }
                for c in self.candidates
            ],
        }


class DesktopResolver:
    """Resolves user-friendly query string to a single resolved DesktopWindow or detects ambiguity."""

    def resolve(self, query: str, windows: List[DesktopWindow]) -> ResolutionResult:
        """Resolves a window reference against a list of active windows.

        Uses deterministic ranking:
        1. Exact Title Match (case-insensitive)
        2. Exact Process Name Match (case-insensitive, ignoring .exe)
        3. Prefix Title Match (case-insensitive)
        4. Substring Title Match (case-insensitive)

        If a level yields matches, it checks for ambiguity. If multiple matches exist,
        it returns AMBIGUOUS instead of silently picking one.

        Args:
            query: The user-friendly window title or process name query.
            windows: The list of visible DesktopWindows.

        Returns:
            ResolutionResult: The resolved window, AMBIGUOUS status with options, or NOT_FOUND.
        """
        if not query or not query.strip():
            return ResolutionResult(ResolutionStatus.NOT_FOUND)

        q = query.strip().lower()

        # Level 1: Exact Title Match
        exact_titles = [w for w in windows if w.title.lower() == q]
        if exact_titles:
            return self._evaluate_candidates(exact_titles)

        # Level 2: Exact Process Name Match (ignore .exe)
        exact_processes = [
            w for w in windows
            if w.process_name.lower() == q or w.process_name.lower().replace(".exe", "") == q
        ]
        if exact_processes:
            return self._evaluate_candidates(exact_processes)

        # Level 3: Prefix Title Match
        prefix_matches = [w for w in windows if w.title.lower().startswith(q)]
        if prefix_matches:
            return self._evaluate_candidates(prefix_matches)

        # Level 4: Substring Title Match
        substring_matches = [w for w in windows if q in w.title.lower()]
        if substring_matches:
            return self._evaluate_candidates(substring_matches)

        return ResolutionResult(ResolutionStatus.NOT_FOUND)

    def _evaluate_candidates(self, candidates: List[DesktopWindow]) -> ResolutionResult:
        if len(candidates) == 1:
            return ResolutionResult(ResolutionStatus.RESOLVED, window=candidates[0])
        
        # Sort candidates deterministically by window_id to ensure stable ambiguity lists
        sorted_candidates = sorted(candidates, key=lambda w: w.window_id)
        return ResolutionResult(ResolutionStatus.AMBIGUOUS, candidates=sorted_candidates)
