"""Diagnostic to verify memory injection affects real agent responses using Ollama."""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add root folder to python path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from app.config.settings import settings
from app.core.logger import JarvisLogger
from app.ai.manager import LLMManager
from app.ai.providers.ollama import OllamaProvider
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor
from app.ai.parser import ResponseParser
from app.agent.runner import AgentRunner
from app.agent.conversation import Conversation
from app.agent.context import ContextManager
from app.agent.controller import AgentController
from app.agent.models import AgentRequest
from app.utils.id_generator import generate_request_id
from datetime import datetime, timezone

from app.memory.models import MemoryType, MemorySource
from app.memory.manager import MemoryManager
from app.memory.repository import SQLiteMemoryRepository
from app.memory.retrieval import LexicalMemoryRetriever
from app.memory.context import MemoryContextBuilder

# Configure basic console logging
JarvisLogger.get_logger("agent_controller")


def main():
    print("============================================================")
    print("Agent Memory Integration Diagnostic")
    print("============================================================\n")

    # Use a temporary SQLite database file to avoid dirtying production jarvis.db
    db_fd, db_path_str = tempfile.mkstemp(suffix=".db")
    db_path = Path(db_path_str)
    os.close(db_fd)

    try:
        # 1. Setup isolated memory subsystems
        repository = SQLiteMemoryRepository(database_path=db_path)
        mem_manager = MemoryManager(repository=repository)
        retriever = LexicalMemoryRetriever(repository=repository)
        context_builder = MemoryContextBuilder()

        # Seed memory
        seeded_content = "The user's name is Anas."
        print(f"Seeding memory: '{seeded_content}'")
        mem_manager.create_memory(
            content=seeded_content,
            memory_type=MemoryType.FACT,
            importance=1.0,
            source=MemorySource.MANUAL
        )

        # 2. Setup real AI and Agent Controller pipelines
        llm_manager = LLMManager()
        ollama_provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        llm_manager.register_provider("ollama", ollama_provider)
        llm_manager.load_provider("ollama")

        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        parser = ResponseParser()

        runner = AgentRunner(
            llm_manager=llm_manager,
            registry=registry,
            executor=executor,
            parser=parser
        )

        conversation = Conversation()
        context_manager = ContextManager()

        controller = AgentController(
            conversation=conversation,
            context_manager=context_manager,
            llm_manager=llm_manager,
            agent_runner=runner,
            retriever=retriever,
            context_builder=context_builder
        )

        # 3. Formulate and send request
        query = "What is my name?"
        print(f"User Query: '{query}'")
        
        request = AgentRequest(
            request_id=generate_request_id(),
            text=query,
            source="diagnostic",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )

        start_time = time.perf_counter()
        
        # We perform retrieve separately first to log diagnostic statistics
        ret_result = retriever.retrieve(query)
        retrieved_count = ret_result.selected_count
        
        # Execute request
        response = controller.process_request(request)
        
        duration = time.perf_counter() - start_time

        print("\nResults:")
        print(f"  Seeded Memory         : {seeded_content}")
        print(f"  User Query            : {query}")
        print(f"  Retrieved Memory Count: {retrieved_count}")
        print(f"  Final Jarvis Response : {response.text}")
        print(f"  Total Duration        : {duration:.2f} seconds")

    finally:
        # Clean up temporary database files
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"Error removing temporary database: {e}")


if __name__ == "__main__":
    main()
