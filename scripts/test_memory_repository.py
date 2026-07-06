"""Isolated local diagnostic script to test Memory persistence and lifecycle operations."""

import tempfile
from pathlib import Path
from app.memory.models import MemoryType, MemorySource
from app.memory.repository import SQLiteMemoryRepository
from app.memory.manager import MemoryManager


def main() -> None:
    """Executes the memory repository diagnostic checks."""
    print("=" * 60)
    print("Memory Repository Diagnostic")
    print("=" * 60)

    # Use a temporary directory context for isolating the diagnostic database
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "diagnostic_jarvis_memories.db"

    try:
        # Initialize SQLiteMemoryRepository with temporary file path
        repo = SQLiteMemoryRepository(database_path=db_path)
        manager = MemoryManager(repo)

        print(f"Temporary database path: {db_path}\n")

        # Create three memories
        m1 = manager.create_memory(
            content="My name is Anas.",
            memory_type=MemoryType.FACT,
            importance=0.9,
            source=MemorySource.MANUAL,
            metadata={"owner": "Anas"}
        )
        print(f"Created FACT memory: ID={m1.memory_id}")

        m2 = manager.create_memory(
            content="I prefer Python for personal projects.",
            memory_type=MemoryType.PREFERENCE,
            importance=0.8,
            source=MemorySource.USER,
            metadata={"language": "Python"}
        )
        print(f"Created PREFERENCE memory: ID={m2.memory_id}")

        m3 = manager.create_memory(
            content="I am building Jarvis AI Assistant.",
            memory_type=MemoryType.PROJECT,
            importance=1.0,
            source=MemorySource.SYSTEM,
            metadata={"project": "Jarvis"}
        )
        print(f"Created PROJECT memory: ID={m3.memory_id}")

        # List all memories
        print("\nListing all memories:")
        print("-" * 40)
        memories = manager.list_memories()
        for m in memories:
            print(f"ID:         {m.memory_id}")
            print(f"Type:       {m.memory_type.value}")
            print(f"Content:    {m.content}")
            print(f"Importance: {m.importance}")
            print(f"Source:     {m.source.value}")
            print("-" * 40)

        # Retrieve one memory by ID
        print(f"\nRetrieving memory by ID: {m2.memory_id}")
        retrieved = manager.get_memory(m2.memory_id)
        if retrieved:
            print(f"Retrieved Content: '{retrieved.content}' (Importance: {retrieved.importance})")
        else:
            print("Failed to retrieve memory.")

        # Update the preference memory importance and content
        print(f"\nUpdating preference memory ID: {m2.memory_id}")
        updated = manager.update_memory(
            memory_id=m2.memory_id,
            content="I prefer Python and Go for personal projects.",
            importance=0.95
        )
        print(f"Updated Content:    '{updated.content}'")
        print(f"Updated Importance: {updated.importance}")

        # Delete one memory (the FACT memory)
        print(f"\nDeleting memory ID: {m1.memory_id}")
        manager.delete_memory(m1.memory_id)
        print("Deletion successful.")

        # Display final count
        count = manager.count_memories()
        print(f"\nFinal Memory Count: {count}")

        # Final List Display
        print("\nFinal memories list:")
        print("-" * 40)
        final_memories = manager.list_memories()
        for m in final_memories:
            print(f"ID:         {m.memory_id}")
            print(f"Type:       {m.memory_type.value}")
            print(f"Content:    {m.content}")
            print(f"Importance: {m.importance}")
            print(f"Source:     {m.source.value}")
            print("-" * 40)

    except Exception as e:
        print(f"Error during memory repository diagnostic execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temporary database files completely
        try:
            temp_dir.cleanup()
            print("\nTemporary database files successfully cleaned up.")
        except Exception as e:
            print(f"\nFailed to clean up temporary directory: {e}")

    print("=" * 60)
    print("Memory Repository Diagnostic Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
