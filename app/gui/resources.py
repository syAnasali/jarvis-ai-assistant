"""ResourceLoader managing fonts, images, and static assets."""

from pathlib import Path
from typing import Optional
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_resources")


class ResourceLoader:
    """Manages application asset paths and static file loading."""

    @classmethod
    def get_asset_path(cls, asset_relative_path: str) -> Path:
        """Returns resolved Path for static assets."""
        return Path("resources") / asset_relative_path
