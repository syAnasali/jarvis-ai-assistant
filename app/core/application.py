"""Main Application Orchestrator."""

from typing import Any, Dict
from app.core.lifecycle import ApplicationState
from app.core.container import ServiceContainer
from app.core.bootstrap import Bootstrap
from app.core.exceptions import ApplicationStartupError
from app.core.constants import DATA_DIR, LOG_DIR, CONFIG_DIR
from app.config.settings import settings
from app.core.logger import JarvisLogger
from app.utils.banner import render_startup_banner, render_shutdown_banner

logger = JarvisLogger.get_logger("application")


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
            self._initialize_llm()
            self._initialize_agent()
            render_startup_banner()
            self._run_chat_loop()
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

        self._shutdown_services()

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

    def _initialize_llm(self) -> None:
        """Sets up the LLMManager and registers the default OllamaProvider."""
        from app.ai.manager import LLMManager
        from app.ai.providers.ollama import OllamaProvider
        
        llm_manager = LLMManager()
        ollama_provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        llm_manager.register_provider("ollama", ollama_provider)
        llm_manager.load_provider("ollama")
        
        self.container.register("llm_manager", llm_manager)

    def _initialize_agent(self) -> None:
        """Instantiates the Conversation, ContextManager, and AgentController."""
        from app.agent.conversation import Conversation
        from app.agent.context import ContextManager
        from app.agent.controller import AgentController
        from app.tools.registry import ToolRegistry
        from app.tools.executor import ToolExecutor
        from app.tools.builtin.system import CurrentTimeTool, SystemInfoTool
        from app.agent.runner import AgentRunner
        from app.ai.parser import ResponseParser

        # 1. Initialize Memory components
        from app.core.constants import DATABASE_PATH
        from app.memory.repository import SQLiteMemoryRepository
        from app.memory.manager import MemoryManager
        from app.memory.retrieval import LexicalMemoryRetriever
        from app.memory.context import MemoryContextBuilder
        from app.memory.parser import MemoryExtractionParser
        from app.memory.extraction import LLMMemoryExtractor
        from app.memory.write_service import MemoryWriteService
        from app.core.exceptions import ApplicationStartupError

        try:
            repository = SQLiteMemoryRepository(database_path=DATABASE_PATH)
            memory_manager = MemoryManager(repository=repository)
            retriever = LexicalMemoryRetriever(repository=repository)
            context_builder = MemoryContextBuilder()

            llm_manager = self.container.get("llm_manager")
            extraction_parser = MemoryExtractionParser()
            extractor = LLMMemoryExtractor(llm_manager=llm_manager)
            write_service = MemoryWriteService(extractor=extractor, memory_manager=memory_manager)

            # Register in container
            self.container.register("memory_repository", repository)
            self.container.register("memory_manager", memory_manager)
            self.container.register("memory_retriever", retriever)
            self.container.register("memory_context_builder", context_builder)
            self.container.register("memory_extraction_parser", extraction_parser)
            self.container.register("memory_extractor", extractor)
            self.container.register("memory_write_service", write_service)
        except Exception as e:
            self.logger.critical(f"Failed to initialize memory subsystem: {e}")
            raise ApplicationStartupError(f"Memory subsystem initialization failed: {e}") from e

        # 2. Create and populate ToolRegistry
        registry = ToolRegistry()
        registry.register(CurrentTimeTool())
        registry.register(SystemInfoTool())

        # 3. Create ToolExecutor
        executor = ToolExecutor(registry)

        # 4. Create parser
        parser = ResponseParser()

        # 5. Create AgentRunner
        agent_runner = AgentRunner(
            llm_manager=llm_manager,
            registry=registry,
            executor=executor,
            parser=parser
        )

        # 6. Register in container
        self.container.register("tool_registry", registry)
        self.container.register("tool_executor", executor)
        self.container.register("agent_runner", agent_runner)

        # 7. Initialize Controller with AgentRunner and Memory components
        conversation = Conversation()
        context_manager = ContextManager()
        controller = AgentController(
            conversation=conversation,
            context_manager=context_manager,
            llm_manager=llm_manager,
            agent_runner=agent_runner,
            retriever=retriever,
            context_builder=context_builder,
            write_service=write_service
        )
        self.container.register("controller", controller)

    def _run_chat_loop(self) -> None:
        """Runs the interactive terminal CLI chat session loop."""
        from app.agent.models import AgentRequest
        from app.core.exceptions import LLMError
        from app.utils.id_generator import generate_request_id
        from datetime import datetime, timezone

        controller = self.container.get("controller")

        while self.state == ApplicationState.RUNNING:
            try:
                user_input = input("You > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nSession interrupted.")
                break

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "bye"):
                render_shutdown_banner()
                break

            request = AgentRequest(
                request_id=generate_request_id(),
                text=user_input,
                source="terminal",
                timestamp=datetime.now(timezone.utc),
                metadata={}
            )

            label_printed = False
            try:
                # Get the streaming iterator
                stream = controller.process_request_stream(request)

                # Iterate over the text chunks
                for chunk in stream:
                    if not label_printed:
                        print("Jarvis > ", end="", flush=True)
                        label_printed = True
                    print(chunk, end="", flush=True)

                if label_printed:
                    print()
                    print()
            except LLMError as le:
                self.logger.error(f"LLM Error during stream: {le}")
                if label_printed:
                    print()
                print(f"Jarvis > [Error] Failed to communicate with model: {le}")
                print()
            except Exception as e:
                self.logger.error(f"Unexpected error processing request stream: {e}")
                if label_printed:
                    print()
                print(f"Jarvis > [Error] An unexpected error occurred: {e}")
                print()

    def _shutdown_services(self) -> None:
        """Shuts down all active registered background connections."""
        try:
            if self.container.has("llm_manager"):
                llm_manager = self.container.get("llm_manager")
                active = llm_manager.active_provider
                if active:
                    active.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down LLM provider: {e}")
