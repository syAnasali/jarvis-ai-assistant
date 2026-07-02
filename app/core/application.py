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
        """Starts the active application execution.

        Initializes LLM services, registers Ollama, builds the AgentController,
        and launches the interactive terminal conversation loop.
        """
        if self.state == ApplicationState.RUNNING:
            self.logger.warning("Application is already running.")
            return

        if self.state != ApplicationState.STOPPED:
            raise ApplicationStartupError(
                f"Cannot run application from state: {self.state.name}. Initialize first."
            )

        self.state = ApplicationState.RUNNING
        self.logger.info("Starting main runtime process...")

        try:
            # 1. Initialize LLMManager and register OllamaProvider
            from app.ai.manager import LLMManager
            from app.ai.providers.ollama import OllamaProvider
            
            llm_manager = LLMManager()
            ollama_provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
            llm_manager.register_provider("ollama", ollama_provider)
            llm_manager.load_provider("ollama")
            
            self.container.register("llm_manager", llm_manager)

            # 2. Initialize Agent components and AgentController
            from app.agent.conversation import Conversation
            from app.agent.context import ContextManager
            from app.agent.controller import AgentController

            conversation = Conversation()
            context_manager = ContextManager()
            controller = AgentController(
                conversation=conversation,
                context_manager=context_manager,
                llm_manager=llm_manager
            )
            self.container.register("controller", controller)

            # 3. Print professional startup banner
            print("==================================================")
            print(f"Application: {settings.app_name}")
            print(f"Version:     {settings.app_version}")
            print(f"Provider:    ollama")
            print(f"Model:       {settings.ollama_model}")
            print("Status:      Ready")
            print("==================================================")
            print("Type 'exit', 'quit', or 'bye' to end the session.")
            print()

            # 4. Terminal chat loop
            import uuid
            from datetime import datetime, timezone
            from app.agent.models import AgentRequest
            from app.core.exceptions import LLMError

            while self.state == ApplicationState.RUNNING:
                try:
                    user_input = input("You > ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\nSession interrupted.")
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "bye"):
                    print("Exiting chat session.")
                    break

                # Create AgentRequest object
                request = AgentRequest(
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    text=user_input,
                    source="terminal",
                    timestamp=datetime.now(timezone.utc),
                    metadata={}
                )

                try:
                    # Process request
                    response = controller.process_request(request)
                    print(f"Jarvis > {response.text}")
                    print()
                except LLMError as le:
                    self.logger.error(f"LLM Error: {le}")
                    print(f"Jarvis > [Error] Failed to communicate with model: {le}")
                    print()
                except Exception as e:
                    self.logger.error(f"Unexpected error processing request: {e}")
                    print(f"Jarvis > [Error] An unexpected error occurred: {e}")
                    print()

        except Exception as e:
            self.state = ApplicationState.ERROR
            self.logger.critical(f"Application crash during main loop: {e}")
            raise ApplicationStartupError(f"Application runtime error: {e}") from e
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully halts the application and releases container singletons."""
        if self.state == ApplicationState.STOPPED:
            return

        self.state = ApplicationState.STOPPING
        self.logger.info("Shutting down core services...")

        # Shutdown active LLM provider if registered
        try:
            if self.container.has("llm_manager"):
                llm_manager = self.container.get("llm_manager")
                active = llm_manager.active_provider
                if active:
                    active.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down LLM provider: {e}")

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
