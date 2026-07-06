"""Diagnostic script to test and verify memory extraction precision and claim-support conservatism."""

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
    print("==============================================================")
    print("Memory Extraction Precision Diagnostic")
    print("==============================================================\n")

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

        positive_cases = [
            "I prefer using Python for my personal projects.",
            "I am currently building a local AI assistant named Jarvis.",
            "My name is Anas."
        ]

        negative_cases = [
            "Write a Python script to reverse a string.",
            "Can you build a simple React application?",
            "Explain Docker containers to me.",
            "Create a website for Sire Media.",
            "Answer this request in a very concise format."
        ]

        # 1. Run Positive Cases
        print("--- RUNNING POSITIVE CASESS (Should Extract and Persist) ---")
        pos_success = 0
        for text in positive_cases:
            print(f"Input: '{text}'")
            res = write_service.write_memories(text)
            print(f"  Extracted: {res.extracted_count}, Persisted: {res.persisted_count}, Rejected: {res.rejected_count}")
            if res.persisted_count > 0:
                pos_success += 1
            else:
                print("  [WARN] Failed to extract or validate durable memory for positive case.")
        print()

        # 2. Run Negative Cases
        print("--- RUNNING NEGATIVE CASES (Should NOT Extract/Persist, Expecting 0) ---")
        neg_false_positives = 0
        for text in negative_cases:
            print(f"Input: '{text}'")
            res = write_service.write_memories(text)
            print(f"  Extracted: {res.extracted_count}, Persisted: {res.persisted_count}, Rejected: {res.rejected_count}")
            if res.persisted_count > 0:
                neg_false_positives += res.persisted_count
                print("  [FAIL] False positive memory persisted!")
        print()

        # 3. Print Results Summary
        print("--- DIAGNOSTIC RESULTS SUMMARY ---")
        total_pos = len(positive_cases)
        total_neg = len(negative_cases)
        print(f"Positive cases recall: {pos_success}/{total_pos} ({pos_success/total_pos*100:.1f}%)")
        print(f"Negative cases false positives: {neg_false_positives} (Expect: 0)")
        
        # Display persisted memories
        print("\nAll Persisted Memories in SQLite DB:")
        memories = memory_manager.list_memories()
        for m in memories:
            print(f"  - [{m.memory_type.value}] '{m.content}' (Source: {m.source.value})")
        print()

        if neg_false_positives == 0:
            print("SUCCESS: 0 false positives recorded!")
            sys.exit(0)
        else:
            print("FAILURE: False positive memory extraction occurred.")
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
