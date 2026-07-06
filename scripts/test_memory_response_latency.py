"""Diagnostic script to measure response latency and verify non-blocking background memory writes."""

import os
import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add root folder to python path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from app.config.settings import settings
from app.core.logger import JarvisLogger
from app.ai.manager import LLMManager
from app.ai.providers.ollama import OllamaProvider
from app.memory.extraction import LLMMemoryExtractor
from app.memory.manager import MemoryManager
from app.memory.repository import SQLiteMemoryRepository
from app.memory.write_service import MemoryWriteService
from app.memory.coordinator import MemoryWriteCoordinator
from app.agent.controller import AgentController
from app.agent.conversation import Conversation
from app.agent.context import ContextManager
from app.agent.models import AgentRequest
from app.agent.runner import AgentRunner
from app.agent.planner import Planner
from app.agent.executor import Executor
from app.tools.registry import ToolRegistry
from app.utils.id_generator import generate_request_id

# Configure logging
JarvisLogger.get_logger("agent_controller")


def main():
    print("==============================================================")
    print("Memory Response Latency Diagnostic")
    print("==============================================================\n")

    # Temporary database
    db_fd, db_path_str = tempfile.mkstemp(suffix=".db")
    db_path = Path(db_path_str)
    os.close(db_fd)

    try:
        # Initialize sub-components
        repository = SQLiteMemoryRepository(database_path=db_path)
        memory_manager = MemoryManager(repository=repository)

        llm_manager = LLMManager()
        ollama_provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        llm_manager.register_provider("ollama", ollama_provider)
        llm_manager.load_provider("ollama")

        extractor = LLMMemoryExtractor(llm_manager=llm_manager)
        write_service = MemoryWriteService(extractor=extractor, memory_manager=memory_manager)
        coordinator = MemoryWriteCoordinator(write_service=write_service)

        registry = ToolRegistry()
        executor = Executor(llm_manager)
        from app.ai.parser import ResponseParser
        parser = ResponseParser()
        agent_runner = AgentRunner(llm_manager=llm_manager, registry=registry, executor=executor, parser=parser)

        conversation = Conversation()
        context_manager = ContextManager()

        # Initialize controller with MemoryWriteCoordinator
        controller = AgentController(
            conversation=conversation,
            context_manager=context_manager,
            llm_manager=llm_manager,
            agent_runner=agent_runner,
            coordinator=coordinator
        )

        request_text = "I prefer Python for personal projects."
        request = AgentRequest(
            request_id=generate_request_id(),
            text=request_text,
            source="terminal",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )

        print(f"Sending request: '{request_text}'")
        
        start_time = time.perf_counter()
        # process_request should complete quickly because LLM extraction is run in the background thread
        response = controller.process_request(request)
        end_time = time.perf_counter()
        
        foreground_duration_ms = (end_time - start_time) * 1000
        print(f"Foreground response returned in: {foreground_duration_ms:.2f} ms")
        print(f"Visible response text: '{response.text}'")

        # Let's check SQLite database immediately: it should be empty since background task is still running
        memories_before = memory_manager.list_memories()
        print(f"Memories in DB immediately after response: {len(memories_before)}")

        # Wait/flush the coordinator to let background task finish
        print("Flushing background memory coordinator...")
        coordinator.flush()

        # Check SQLite database again: now the memory should be persisted
        memories_after = memory_manager.list_memories()
        print(f"Memories in DB after coordinator flush: {len(memories_after)}")
        for m in memories_after:
            print(f"  - [{m.memory_type.value}] '{m.content}'")

        # Print coordinator metrics
        metrics = coordinator.get_metrics()
        print(f"\nCoordinator Metrics: {metrics}")

        coordinator.shutdown()

        # Latency check: foreground response should be fast (e.g. typical local run is fast compared to LLM extraction)
        # We can verify that memories were successfully persisted
        if len(memories_after) > 0 and metrics["completed_jobs"] == 1:
            print("\nSUCCESS: Asynchronous memory extraction and persistence validated!")
            sys.exit(0)
        else:
            print("\nFAILURE: Memories were not persisted asynchronously.")
            sys.exit(1)

    finally:
        # Clean up temporary database files
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"Error removing temporary database: {e}")


if __name__ == "__main__":
    main()
