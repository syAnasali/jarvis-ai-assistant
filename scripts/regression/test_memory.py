import time
from pathlib import Path
from datetime import datetime, timezone
from app.memory.repository import SQLiteMemoryRepository
from app.memory.manager import MemoryManager
from app.memory.models import Memory, MemoryType, MemorySource

def run_regression() -> dict:
    start_time = time.perf_counter()
    db_path = Path("test_mem_db.sqlite")
    try:
        # SQLiteMemoryRepository automatically initializes the database inside constructor
        repo = SQLiteMemoryRepository(database_path=db_path)
        manager = MemoryManager(repository=repo)
        
        # Verify save memory with all required fields (importance and source)
        mem = Memory(
            memory_id="test_mem_001",
            content="This is a regression test memory entry",
            memory_type=MemoryType.FACT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            importance=0.8,
            source=MemorySource.USER
        )
        
        repo.add(mem)
        
        # Verify read memory
        fetched = repo.get("test_mem_001")
        if not fetched or fetched.content != mem.content:
            raise ValueError(f"Fetched memory content mismatch. Got: {fetched}")
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_memory.py",
            "status": "PASS",
            "duration": duration,
            "reason": "Memory save and retrieve verification succeeded on SQLite memory repository."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_memory.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Memory test failed: {e}"
        }
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                pass
        # Clean up journal file if created
        journal = Path("test_mem_db.sqlite-journal")
        if journal.exists():
            try:
                journal.unlink()
            except Exception:
                pass
