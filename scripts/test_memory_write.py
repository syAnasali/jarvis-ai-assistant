"""Diagnostic to test memory write service and duplicate detection."""

import os
import sys
import tempfile
from pathlib import Path

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

# Configure logging
JarvisLogger.get_logger("agent_controller")


def main():
    print("============================================================")
    print("Memory Write Diagnostic")
    print("============================================================\n")

    # Temporary database
    db_fd, db_path_str = tempfile.mkstemp(suffix=".db")
    db_path = Path(db_path_str)
    os.close(db_fd)

    try:
        # Initialize components
        repository = SQLiteMemoryRepository(database_path=db_path)
        memory_manager = MemoryManager(repository=repository)

        llm_manager = LLMManager()
        ollama_provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        llm_manager.register_provider("ollama", ollama_provider)
        llm_manager.load_provider("ollama")

        extractor = LLMMemoryExtractor(llm_manager=llm_manager)
        write_service = MemoryWriteService(extractor=extractor, memory_manager=memory_manager)

        # Run 1: First insertion
        text1 = "My name is Anas."
        print(f"Run 1: Sending '{text1}'")
        res1 = write_service.write_memories(text1)
        print(f"  Extracted : {res1.extracted_count}")
        print(f"  Persisted : {res1.persisted_count}")
        print(f"  Duplicates: {res1.duplicate_count}")
        print(f"  Rejected  : {res1.rejected_count}")
        print()

        # Run 2: Duplicate insertion
        text2 = "My name is Anas."
        print(f"Run 2: Sending '{text2}' (same statement)")
        res2 = write_service.write_memories(text2)
        print(f"  Extracted : {res2.extracted_count}")
        print(f"  Persisted : {res2.persisted_count}")
        print(f"  Duplicates: {res2.duplicate_count}")
        print(f"  Rejected  : {res2.rejected_count}")
        print()

        # Run 3: No-memory text
        text3 = "Explain photosynthesis."
        print(f"Run 3: Sending '{text3}' (should extract no memories)")
        res3 = write_service.write_memories(text3)
        print(f"  Extracted : {res3.extracted_count}")
        print(f"  Persisted : {res3.persisted_count}")
        print(f"  Duplicates: {res3.duplicate_count}")
        print(f"  Rejected  : {res3.rejected_count}")
        print()

        # Display all memories in database
        print("Persisted Memories in Database:")
        memories = memory_manager.list_memories()
        print(f"Total count: {len(memories)}")
        for m in memories:
            print(f"  - [{m.memory_type.value}] '{m.content}' (Importance: {m.importance}, Source: {m.source.value})")
        print()

    finally:
        # Clean up temporary database files
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"Error removing temporary database: {e}")


if __name__ == "__main__":
    main()
