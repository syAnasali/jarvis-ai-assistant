import time
from pathlib import Path
from datetime import datetime, timezone
from app.conversation.repository import SQLiteConversationRepository
from app.conversation.manager import ConversationManager
from app.agent.messages import Message, MessageRole

def run_regression() -> dict:
    start_time = time.perf_counter()
    db_path = Path("test_conv_db.sqlite")
    try:
        repo = SQLiteConversationRepository(database_path=db_path)
        manager = ConversationManager(repository=repo)
        session = manager.create_session()
        
        # Test adding user and assistant messages
        msg1 = Message(
            id="msg_001",
            role=MessageRole.USER,
            content="Hello Jarvis",
            timestamp=datetime.now(timezone.utc)
        )
        msg2 = Message(
            id="msg_002",
            role=MessageRole.ASSISTANT,
            content="Hello! How can I help you?",
            timestamp=datetime.now(timezone.utc)
        )
        
        manager.add_message(session.session_id, msg1)
        manager.add_message(session.session_id, msg2)
        
        # Test retrieving messages using get_messages method on ConversationManager
        history = manager.get_messages(session.session_id)
        if len(history) != 2:
            raise ValueError(f"History message count mismatch. Expected 2, got {len(history)}")
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_conversation.py",
            "status": "PASS",
            "duration": duration,
            "reason": "Successfully verified conversation database session creation and history tracking."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_conversation.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Conversation test failed: {e}"
        }
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                pass
        # Clean up journal file if created
        journal = Path("test_conv_db.sqlite-journal")
        if journal.exists():
            try:
                journal.unlink()
            except Exception:
                pass
