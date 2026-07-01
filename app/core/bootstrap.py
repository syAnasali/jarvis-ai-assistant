"""Bootstrapping logic for initial system setup."""

from pathlib import Path
from typing import List
from app.core.constants import DATA_DIR, LOG_DIR, CONFIG_DIR
from app.core.logger import JarvisLogger
from app.config.settings import settings

logger = JarvisLogger.get_logger("bootstrap")


class DirectoryManager:
    """Manages creation and verification of application directories."""

    def __init__(self, directories: List[Path] | None = None) -> None:
        """Initializes DirectoryManager with a list of directories.

        Args:
            directories: Optional list of directories to manage.
        """
        self._directories = directories or [DATA_DIR, LOG_DIR, CONFIG_DIR]

    def add_directory(self, path: Path) -> None:
        """Adds a new directory to be managed.

        Args:
            path: Path of the directory.
        """
        if path not in self._directories:
            self._directories.append(path)

    def verify_and_create(self) -> bool:
        """Ensures all managed directories exist.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            for directory in self._directories:
                directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            # Output error to stderr in case logging isn't fully configured
            print(f"Error creating directories: {e}")
            return False


class Bootstrap:
    """Orchestrates the application setup phase (logging, config, directories)."""

    def __init__(self) -> None:
        """Initializes the Bootstrap manager."""
        self.directory_manager = DirectoryManager()

    def setup(self) -> bool:
        """Runs the bootstrapping process to initialize all sub-systems.

        Returns:
            bool: True if bootstrapping succeeded, False otherwise.
        """
        try:
            # 1. Verify and create directories
            if not self.directory_manager.verify_and_create():
                return False

            # 2. Configure logging with user settings
            JarvisLogger.configure(log_level=settings.log_level, log_dir=str(LOG_DIR))
            
            logger.info("Bootstrap process completed successfully.")
            return True
        except Exception as e:
            print(f"Bootstrap execution failed: {e}")
            return False
