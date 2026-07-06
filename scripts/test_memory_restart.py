"""Cross-Restart Memory Persistence Diagnostic."""

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

from app.memory.manager import MemoryManager
from app.memory.repository import SQLiteMemoryRepository
from app.memory.retrieval import LexicalMemoryRetriever
from app.memory.context import MemoryContextBuilder
from app.memory.extraction import LLMMemoryExtractor
from app.memory.parser import MemoryExtractionParser
from app.memory.write_service import MemoryWriteService

# Configure logging
JarvisLogger.get_logger("agent_controller")


def main():
    print("============================================================")
    print("Cross-Restart Memory Diagnostic")
    print("============================================================\n")

    # Temporary database
    db_fd, db_path_str = tempfile.mkstemp(suffix=".db")
    db_path = Path(db_path_str)
    os.close(db_fd)

    phase1_response_text = ""
    phase1_persisted_count = 0
    phase2_retrieved_count = 0
    phase2_response_text = ""

    try:
        # ----------------------------------------------------------
        # PHASE 1: Automatic Extraction and Persistence
        # ----------------------------------------------------------
        print("--- PHASE 1: Initializing Agent Pipeline ---")
        repository1 = SQLiteMemoryRepository(database_path=db_path)
        manager1 = MemoryManager(repository=repository1)
        retriever1 = LexicalMemoryRetriever(repository=repository1)
        context_builder1 = MemoryContextBuilder()

        llm_manager = LLMManager()
        ollama_provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        llm_manager.register_provider("ollama", ollama_provider)
        llm_manager.load_provider("ollama")

        extractor1 = LLMMemoryExtractor(llm_manager=llm_manager)
        write_service1 = MemoryWriteService(extractor=extractor1, memory_manager=manager1)

        registry1 = ToolRegistry()
        executor1 = ToolExecutor(registry1)
        parser1 = ResponseParser()
        runner1 = AgentRunner(llm_manager, registry1, executor1, parser1)

        conversation1 = Conversation()
        context_manager1 = ContextManager()

        controller1 = AgentController(
            conversation=conversation1,
            context_manager=context_manager1,
            llm_manager=llm_manager,
            agent_runner=runner1,
            retriever=retriever1,
            context_builder=context_builder1,
            write_service=write_service1
        )

        user_statement = "My name is Anas."
        print(f"Sending User Statement: '{user_statement}'")
        
        req1 = AgentRequest(
            request_id=generate_request_id(),
            text=user_statement,
            source="restart_test",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )

        resp1 = controller1.process_request(req1)
        phase1_response_text = resp1.text
        
        # Verify count in repository
        phase1_persisted_count = repository1.count()
        print(f"Phase 1 complete. Response: '{phase1_response_text}'")
        print(f"Phase 1 memories persisted in SQLite: {phase1_persisted_count}\n")

        # Destroy pipeline 1
        del repository1, manager1, retriever1, context_builder1, extractor1, write_service1, controller1
        print("Pipeline 1 destroyed/closed.\n")

        # ----------------------------------------------------------
        # PHASE 2: Fresh Pipeline Reconstructed and Retrieval Checked
        # ----------------------------------------------------------
        print("--- PHASE 2: Reconstructing Fresh Pipeline from SQLite ---")
        repository2 = SQLiteMemoryRepository(database_path=db_path)
        manager2 = MemoryManager(repository=repository2)
        retriever2 = LexicalMemoryRetriever(repository=repository2)
        context_builder2 = MemoryContextBuilder()

        extractor2 = LLMMemoryExtractor(llm_manager=llm_manager)
        write_service2 = MemoryWriteService(extractor=extractor2, memory_manager=manager2)

        registry2 = ToolRegistry()
        executor2 = ToolExecutor(registry2)
        parser2 = ResponseParser()
        runner2 = AgentRunner(llm_manager, registry2, executor2, parser2)

        conversation2 = Conversation()
        context_manager2 = ContextManager()

        controller2 = AgentController(
            conversation=conversation2,
            context_manager=context_manager2,
            llm_manager=llm_manager,
            agent_runner=runner2,
            retriever=retriever2,
            context_builder=context_builder2,
            write_service=write_service2
        )

        query = "What is my name?"
        print(f"Sending Query to Fresh Pipeline: '{query}'")

        # Retrieve count
        ret_result = retriever2.retrieve(query)
        phase2_retrieved_count = ret_result.selected_count

        req2 = AgentRequest(
            request_id=generate_request_id(),
            text=query,
            source="restart_test",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )

        resp2 = controller2.process_request(req2)
        phase2_response_text = resp2.text

        print(f"Phase 2 complete. Response: '{phase2_response_text}'\n")

        # Display output report
        print("============================================================")
        print("Cross-Restart Memory Diagnostic Report")
        print("============================================================")
        print("Phase 1:")
        print(f"  User Statement       : {user_statement}")
        print(f"  Jarvis Response      : {phase1_response_text}")
        print(f"  Persisted Memory Count: {phase1_persisted_count}")
        print()
        print("Phase 2:")
        print("  Fresh Repository Created  : yes")
        print("  Fresh Conversation Created: yes")
        print(f"  User Query           : {query}")
        print(f"  Retrieved Memory Count: {phase2_retrieved_count}")
        print(f"  Jarvis Response      : {phase2_response_text}")
        print("============================================================\n")

    finally:
        # Clean up temporary database files
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"Error removing temporary database: {e}")


if __name__ == "__main__":
    main()
