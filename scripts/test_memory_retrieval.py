"""Manual memory retrieval diagnostic script."""

import os
import sys
import tempfile
from pathlib import Path

# Add root folder to python path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from app.memory.models import MemoryType, MemorySource
from app.memory.manager import MemoryManager
from app.memory.repository import SQLiteMemoryRepository
from app.memory.retrieval import LexicalMemoryRetriever
from app.memory.context import MemoryContextBuilder


def main():
    print("============================================================")
    print("Memory Retrieval Diagnostic")
    print("Retriever: Determinical Lexical Retriever")
    print("============================================================\n")

    # Use a temporary SQLite database file
    db_fd, db_path_str = tempfile.mkstemp(suffix=".db")
    db_path = Path(db_path_str)
    os.close(db_fd)

    try:
        # Initialize real memory abstractions
        repository = SQLiteMemoryRepository(database_path=db_path)
        manager = MemoryManager(repository=repository)
        retriever = LexicalMemoryRetriever(repository=repository)
        context_builder = MemoryContextBuilder()

        # Seed memories
        print("Seeding memories...")
        # 1. Fact
        mem1 = manager.create_memory(
            content="The user's name is Anas.",
            memory_type=MemoryType.FACT,
            importance=0.9,
            source=MemorySource.MANUAL
        )
        # 2. Preference
        mem2 = manager.create_memory(
            content="The user prefers Python for personal projects.",
            memory_type=MemoryType.PREFERENCE,
            importance=0.85,
            source=MemorySource.MANUAL
        )
        # 3. Project
        mem3 = manager.create_memory(
            content="The user is building Jarvis AI Assistant.",
            memory_type=MemoryType.PROJECT,
            importance=0.8,
            source=MemorySource.MANUAL
        )
        # 4. Context
        mem4 = manager.create_memory(
            content="The user is studying computer science.",
            memory_type=MemoryType.CONTEXT,
            importance=0.7,
            source=MemorySource.MANUAL
        )
        # Noise memories
        mem_noise1 = manager.create_memory(
            content="Water boils at 100 degrees Celsius under standard atmospheric pressure.",
            memory_type=MemoryType.FACT,
            importance=0.3,
            source=MemorySource.MANUAL
        )
        mem_noise2 = manager.create_memory(
            content="The capital city of France is Paris.",
            memory_type=MemoryType.FACT,
            importance=0.3,
            source=MemorySource.MANUAL
        )

        print(f"Total candidate memories persisted: {repository.count()}\n")

        # Test queries
        queries = [
            "What is my name?",
            "What programming language do I prefer for personal projects?",
            "What project am I building?",
            "What am I studying?",
            "Explain photosynthesis."
        ]

        for query in queries:
            print(f"Query: '{query}'")
            # Retrieve
            result = retriever.retrieve(query)
            print(f"  Candidate count      : {result.total_candidates}")
            print(f"  Selected count       : {result.selected_count}")
            
            if result.selected_count > 0:
                ids = [match.memory.memory_id for match in result.matches]
                types = [match.memory.memory_type.value for match in result.matches]
                lexical_scores = [round(match.lexical_score, 4) for match in result.matches]
                relevance_scores = [round(match.relevance_score, 4) for match in result.matches]
                
                print(f"  Selected memory IDs  : {ids}")
                print(f"  Selected memory types: {types}")
                print(f"  Lexical scores       : {lexical_scores}")
                print(f"  Relevance scores     : {relevance_scores}")
                
                # Context built
                context_str = context_builder.build(list(result.matches))
                print("  Built memory context :")
                print("----------------------------------------")
                print(context_str)
                print("----------------------------------------")
            else:
                print("  Selected memory IDs  : []")
                print("  Selected memory types: []")
                print("  Lexical scores       : []")
                print("  Relevance scores     : []")
                print("  Built memory context : (empty)")
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
