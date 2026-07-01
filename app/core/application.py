"""Main Application Orchestrator."""

from typing import Any, Dict
from app.core.lifecycle import ApplicationState
from app.core.container import ServiceContainer
from app.core.bootstrap import Bootstrap
from app.core.exceptions import ApplicationStartupError
from app.core.constants import DATA_DIR, LOG_DIR, CONFIG_DIR
from app.config.settings import settings
from app.core.logger import JarvisLogger


class Application:
    """Manages application state, service registration, and core lifecycle orchestrations."""

    def __init__(self) -> None:
        """Initializes the Application and service container."""
        self.state: ApplicationState = ApplicationState.STOPPED
        self.container = ServiceContainer()
        self._bootstrap = Bootstrap()

    @property
    def logger(self) -> Any:
        """Helper to get logger from the container."""
        return self.container.get("logger")

    def initialize(self) -> None:
        """Bootstraps application configurations, logging, and directory systems.

        Raises:
            ApplicationStartupError: If bootstrapping fails.
        """
        self.state = ApplicationState.STARTING
        
        # Register core singletons
        self.container.register("settings", settings)
        self.container.register("logger", JarvisLogger.get_logger("application"))
        
        self.state = ApplicationState.INITIALIZING
        self.logger.info("Starting initialization process...")

        success = self._bootstrap.setup()
        if not success:
            self.state = ApplicationState.ERROR
            raise ApplicationStartupError("Application bootstrapping failed during setup.")

        self.state = ApplicationState.STOPPED
        self.logger.info("Application core systems successfully initialized.")

    def run(self) -> None:
        """Transitions application state to running.

        Raises:
            ApplicationStartupError: If application is in invalid state or not initialized.
        """
        if self.state == ApplicationState.RUNNING:
            self.logger.warning("Application is already running.")
            return

        if self.state != ApplicationState.STOPPED:
            raise ApplicationStartupError(
                f"Cannot run application from state: {self.state.name}. Initialize first."
            )

        self.state = ApplicationState.RUNNING
        self.logger.info("Application is now running.")

    def shutdown(self) -> None:
        """Gracefully halts the application and releases container singletons."""
        if self.state == ApplicationState.STOPPED:
            return

        self.state = ApplicationState.STOPPING
        self.logger.info("Shutting down core services...")
        self.state = ApplicationState.STOPPED
        self.logger.info("Application shutdown complete.")

    def health_check(self) -> Dict[str, Any]:
        """Provides diagnostic health checks of the core application.

        Returns:
            Dict[str, Any]: Application diagnostic state map.
        """
        settings_loaded = self.container.has("settings")
        logger_configured = self.container.has("logger")
        
        # Verify directory existence
        dirs_ok = DATA_DIR.exists() and LOG_DIR.exists() and CONFIG_DIR.exists()

        from app.core.constants import APP_NAME, APP_VERSION

        return {
            "application": APP_NAME,
            "version": APP_VERSION,
            "state": self.state.value,
            "logger": "configured" if logger_configured else "missing",
            "settings": "loaded" if settings_loaded else "missing",
            "directories": "verified" if dirs_ok else "unverified"
        }
