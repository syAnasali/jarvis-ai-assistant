"""Controlled Windows Desktop Interaction Runtime Services."""

from app.services.desktop.models import DesktopWindow, DesktopMetrics
from app.services.desktop.policy import DesktopPolicy
from app.services.desktop.resolver import (
    ResolutionResult,
    ResolutionStatus,
    DesktopResolver,
)
from app.services.desktop.backend import DesktopBackend, WindowsDesktopBackend
from app.services.desktop.service import DesktopService

__all__ = [
    "DesktopWindow",
    "DesktopMetrics",
    "DesktopPolicy",
    "ResolutionResult",
    "ResolutionStatus",
    "DesktopResolver",
    "DesktopBackend",
    "WindowsDesktopBackend",
    "DesktopService",
]
