"""Application resolution and launching package."""

from app.services.applications.models import InstalledApplication
from app.services.applications.resolver import ApplicationResolver, ApplicationResolution
from app.services.applications.launcher import ApplicationLauncher

__all__ = [
    "InstalledApplication",
    "ApplicationResolver",
    "ApplicationResolution",
    "ApplicationLauncher",
]
