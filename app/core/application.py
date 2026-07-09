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
            active_session = self.container.get("conversation_active_session")
            print(f"Session: {active_session.session_id}")
            print()
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
        from app.ai.scheduler import PriorityInferenceScheduler
        from app.ai.manager import LLMManager
        from app.ai.providers.ollama import OllamaProvider
        
        # Initialize and start PriorityInferenceScheduler
        scheduler = PriorityInferenceScheduler()
        scheduler.start()
        self.container.register("inference_scheduler", scheduler)
        
        llm_manager = LLMManager(scheduler=scheduler)
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
        from app.memory.coordinator import MemoryWriteCoordinator
        from app.core.exceptions import ApplicationStartupError

        try:
            repository = SQLiteMemoryRepository(database_path=DATABASE_PATH)
            memory_manager = MemoryManager(repository=repository)
            retriever = LexicalMemoryRetriever(repository=repository)
            context_builder = MemoryContextBuilder()

            llm_manager = self.container.get("llm_manager")
            extraction_parser = MemoryExtractionParser()
            extractor = LLMMemoryExtractor(llm_manager=llm_manager)

            from app.memory.related import RelatedMemoryFinder
            from app.memory.resolver import LLMMemoryResolver
            from app.memory.resolution import MemoryResolutionValidator, MemoryResolutionExecutor

            related_finder = RelatedMemoryFinder()
            resolver = LLMMemoryResolver(llm_manager=llm_manager)
            validator = MemoryResolutionValidator()
            executor = MemoryResolutionExecutor(memory_manager=memory_manager)

            write_service = MemoryWriteService(
                extractor=extractor,
                memory_manager=memory_manager,
                related_finder=related_finder,
                resolver=resolver,
                validator=validator,
                executor=executor
            )
            coordinator = MemoryWriteCoordinator(write_service=write_service)

            # Register in container
            self.container.register("memory_repository", repository)
            self.container.register("memory_manager", memory_manager)
            self.container.register("memory_retriever", retriever)
            self.container.register("memory_context_builder", context_builder)
            self.container.register("memory_extraction_parser", extraction_parser)
            self.container.register("memory_extractor", extractor)
            self.container.register("memory_related_finder", related_finder)
            self.container.register("memory_resolver", resolver)
            self.container.register("memory_resolution_validator", validator)
            self.container.register("memory_resolution_executor", executor)
            self.container.register("memory_write_service", write_service)
            self.container.register("memory_coordinator", coordinator)
        except Exception as e:
            self.logger.critical(f"Failed to initialize memory subsystem: {e}")
            raise ApplicationStartupError(f"Memory subsystem initialization failed: {e}") from e

        # 1.5. Initialize Conversation Persistence components
        from app.conversation.repository import SQLiteConversationRepository
        from app.conversation.manager import ConversationManager
        from app.conversation.policy import ContextWindowPolicy

        try:
            conv_repository = SQLiteConversationRepository(database_path=DATABASE_PATH)
            conversation_manager = ConversationManager(repository=conv_repository)
            context_policy = ContextWindowPolicy()
            active_session = conversation_manager.create_session()

            self.container.register("conversation_repository", conv_repository)
            self.container.register("conversation_manager", conversation_manager)
            self.container.register("conversation_context_policy", context_policy)
            self.container.register("conversation_active_session", active_session)
        except Exception as e:
            self.logger.critical(f"Failed to initialize conversation subsystem: {e}")
            raise ApplicationStartupError(f"Conversation subsystem initialization failed: {e}") from e

        # 1.6. Initialize Action Approval components
        from app.approval.repository import SQLiteApprovalRepository
        from app.approval.manager import ApprovalManager

        try:
            approval_repository = SQLiteApprovalRepository(database_path=DATABASE_PATH)
            approval_manager = ApprovalManager(
                repository=approval_repository,
                timeout_seconds=settings.approval_timeout_seconds
            )
            self.container.register("approval_repository", approval_repository)
            self.container.register("approval_manager", approval_manager)
        except Exception as e:
            self.logger.critical(f"Failed to initialize approval subsystem: {e}")
            raise ApplicationStartupError(f"Approval subsystem initialization failed: {e}") from e

        # 2. Create and populate ToolRegistry
        from app.tools.builtin.disk import GetDiskUsageTool
        from app.tools.builtin.process import ListRunningProcessesTool, FindRunningProcessTool
        from app.tools.builtin.applications import (
            ListInstalledApplicationsTool,
            FindInstalledApplicationTool,
            ResolveApplicationTool,
            LaunchApplicationTool
        )
        from app.tools.builtin.filesystem import (
            InspectPathTool,
            ListDirectoryTool,
            CreateDirectoryTool,
            WriteTextFileTool,
            MovePathTool,
            DeletePathTool,
        )
        from app.services.filesystem.policy import FilesystemPolicy
        from app.services.filesystem.resolver import FilesystemResolver
        from app.services.filesystem.service import FilesystemService

        policy = FilesystemPolicy()
        resolver = FilesystemResolver(policy)
        filesystem_service = FilesystemService(
            policy=policy,
            resolver=resolver,
            list_max_entries=settings.filesystem_list_max_entries,
            write_max_chars=settings.filesystem_write_max_chars,
            relative_path_max_length=settings.filesystem_relative_path_max_length
        )
        self.container.register("filesystem_service", filesystem_service)

        registry = ToolRegistry()
        registry.register(CurrentTimeTool())
        registry.register(SystemInfoTool())
        registry.register(GetDiskUsageTool())
        registry.register(ListRunningProcessesTool())
        registry.register(FindRunningProcessTool())
        registry.register(ListInstalledApplicationsTool())
        registry.register(FindInstalledApplicationTool())
        registry.register(ResolveApplicationTool())
        registry.register(LaunchApplicationTool())
        
        # Register new filesystem tools
        registry.register(InspectPathTool(filesystem_service))
        registry.register(ListDirectoryTool(filesystem_service))
        registry.register(CreateDirectoryTool(filesystem_service))
        registry.register(WriteTextFileTool(filesystem_service))
        registry.register(MovePathTool(filesystem_service))
        registry.register(DeletePathTool(filesystem_service))

        # 3. Create ToolExecutor with approval manager
        executor = ToolExecutor(registry, approval_manager)

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

        # 6.5. Initialize Planning components
        from app.planning.router import ExecutionRouter
        from app.planning.planner import LLMTaskPlanner
        from app.planning.validator import PlanValidator
        from app.planning.executor import TaskExecutor

        planning_router = ExecutionRouter()
        planning_planner = LLMTaskPlanner(llm_manager)
        planning_validator = PlanValidator(registry)
        task_executor = TaskExecutor(llm_manager, registry, executor, planning_validator)

        self.container.register("planning_router", planning_router)
        self.container.register("planning_planner", planning_planner)
        self.container.register("planning_validator", planning_validator)
        self.container.register("planning_executor", task_executor)

        # 7. Initialize Controller with AgentRunner, Memory, and Approval components
        conversation = Conversation()
        context_manager = ContextManager()
        controller = AgentController(
            conversation=conversation,
            context_manager=context_manager,
            llm_manager=llm_manager,
            agent_runner=agent_runner,
            retriever=retriever,
            context_builder=context_builder,
            coordinator=coordinator,
            conversation_manager=conversation_manager,
            context_policy=context_policy,
            router=planning_router,
            planner=planning_planner,
            validator=planning_validator,
            executor=task_executor,
            approval_manager=approval_manager
        )
        controller.active_session_id = active_session.session_id
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

            try:
                active_approval_id = None
                while True:
                    label_printed = False
                    stream = controller.process_request_stream(request, approval_action_id=active_approval_id)

                    for chunk in stream:
                        if not label_printed:
                            print("Jarvis > ", end="", flush=True)
                            label_printed = True
                        print(chunk, end="", flush=True)

                    if label_printed:
                        print()
                        print()

                    # Check if suspended for confirmation
                    messages = controller.conversation.get_history()
                    if messages:
                        last_msg = messages[-1]
                        if last_msg.role.value == "assistant" and last_msg.metadata.get("confirmation_required"):
                            action_id = last_msg.metadata.get("pending_action_id")
                            tool_name = last_msg.metadata.get("tool_name")
                            reason = last_msg.metadata.get("reason", "")
                            
                            approval_manager = self.container.get("approval_manager")
                            action = approval_manager.get(action_id)
                            if action:
                                from app.approval.cli import prompt_user_approval
                                approved = prompt_user_approval(tool_name, reason, action.arguments, action.metadata)
                                if approved:
                                    approval_manager.approve(action_id)
                                    active_approval_id = action_id
                                    # Continue loop to resume with approved action
                                    continue
                                else:
                                    approval_manager.reject(action_id)
                                    active_approval_id = action_id
                                    # Continue loop to resume with rejected action (and output cancellation response)
                                    continue
                    break  # Break out of loop if not suspended or no more approvals needed
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
        # 1. Shutdown memory coordinator first (flushes pending jobs)
        try:
            if self.container.has("memory_coordinator"):
                coordinator = self.container.get("memory_coordinator")
                coordinator.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down memory coordinator: {e}")

        # 1b. Shutdown inference scheduler (waits for queued jobs to complete)
        try:
            if self.container.has("inference_scheduler"):
                scheduler = self.container.get("inference_scheduler")
                scheduler.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down inference scheduler: {e}")

        # 2. Shutdown active LLM provider afterward
        try:
            if self.container.has("llm_manager"):
                llm_manager = self.container.get("llm_manager")
                active = llm_manager.active_provider
                if active:
                    active.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down LLM provider: {e}")
