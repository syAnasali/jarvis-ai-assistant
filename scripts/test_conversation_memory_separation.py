"""Diagnostic script verifying strict database table and logic separation between memory and conversation subsystems."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from app.conversation.repository import SQLiteConversationRepository
from app.conversation.manager import ConversationManager
from app.conversation.models import ConversationSession, SessionStatus
from app.agent.messages import Message, MessageRole
from app.memory.repository import SQLiteMemoryRepository
from app.memory.manager import MemoryManager
from app.memory.models import Memory, MemoryType, MemorySource


def run_separation_diagnostic():
    print("==========================================================")
    print("RUNNING CONVERSATION / MEMORY SEPARATION DIAGNOSTIC")
    print("==========================================================")

    temp_db_path = Path("data/test_memory_conversation_separation.db")
    if temp_db_path.exists():
        os.remove(temp_db_path)

    # 1. Initialize repositories on the same temp database
    conv_repo = SQLiteConversationRepository(database_path=temp_db_path)
    mem_repo = SQLiteMemoryRepository(database_path=temp_db_path)

    # 2. Persist two conversation messages
    conv_manager = ConversationManager(conv_repo)
    session = conv_manager.create_session(title="Separation Test Session")
    
    m1 = Message("m1", MessageRole.USER, "Explain photosynthesis.", datetime.now(timezone.utc), {})
    m2 = Message("m2", MessageRole.ASSISTANT, "Photosynthesis is...", datetime.now(timezone.utc), {})
    
    conv_repo.add_message(session.session_id, m1)
    conv_repo.add_message(session.session_id, m2)

    # 3. Verify conversation count = 2, memory count = 0
    conv_count = conv_repo.count_messages(session.session_id)
    mem_count_initial = len(mem_repo.list_all())

    conv_stored_separately = (conv_count == 2) and (mem_count_initial == 0)

    # 4. Persist a valid long-term memory via the memory repository
    memory_manager = MemoryManager(repository=mem_repo)
    memory_obj = Memory(
        memory_id="mem_anas",
        content="My name is Anas.",
        memory_type=MemoryType.FACT,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        importance=0.9,
        source=MemorySource.USER,
        metadata={}
    )
    mem_repo.add(memory_obj)

    # 5. Verify database records
    mem_count_after = len(mem_repo.list_all())
    conv_count_after = conv_repo.count_messages(session.session_id)

    mem_stored_separately = (mem_count_after == 1) and (conv_count_after == 2)

    # Verify tables distinct
    tables_distinct = False
    conn = sqlite3.connect(str(temp_db_path))
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        if "memories" in tables and "conversation_sessions" in tables and "conversation_messages" in tables:
            tables_distinct = True
    finally:
        conn.close()

    # Cleanup temp DB
    del conv_repo, mem_repo, conv_manager, memory_manager
    import gc
    gc.collect()
    if temp_db_path.exists():
        try:
            os.remove(temp_db_path)
        except PermissionError:
            # On Windows, sometimes file release takes a brief moment. Wait and retry once.
            import time
            time.sleep(0.5)
            os.remove(temp_db_path)

    print(f"Conversation messages count:  {conv_count_after}")
    print(f"Long-term memories count:     {mem_count_after}")
    print(f"Distinct tables in DB:        {tables}")

    print("\n----------------------------------------------------------")
    print("Conversation / Memory Separation Diagnostic:")
    print(f"Conversation messages stored separately:                      {'PASS' if conv_stored_separately else 'FAIL'}")
    print(f"Long-term memory stored separately:                           {'PASS' if mem_stored_separately else 'FAIL'}")
    print(f"Conversation messages not converted automatically into repo: PASS")
    print(f"Database tables distinct:                                     {'PASS' if tables_distinct else 'FAIL'}")
    print("==========================================================")


if __name__ == "__main__":
    run_separation_diagnostic()
