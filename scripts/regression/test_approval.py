import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from app.approval.repository import SQLiteApprovalRepository
from app.approval.models import PendingAction, PendingActionStatus
from app.tools.models import ToolPermission

def run_regression() -> dict:
    start_time = time.perf_counter()
    db_path = Path("test_appr_db.sqlite")
    try:
        repo = SQLiteApprovalRepository(database_path=db_path)
        
        now = datetime.now(timezone.utc)
        # Verify PendingAction insert with all required fields
        action = PendingAction(
            action_id="act_001",
            tool_name="create_file",
            arguments={"root": "desktop", "relative_path": "notes.txt"},
            permission_level=ToolPermission.CONFIRMATION,
            status=PendingActionStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(seconds=120),
            reason="test"
        )
        repo.add(action)
        
        # Verify Status Updates
        repo.update_status("act_001", PendingActionStatus.APPROVED)
        fetched = repo.get("act_001")
        
        if not fetched or fetched.status != PendingActionStatus.APPROVED:
            raise ValueError(f"Fetched action status mismatch. Got: {fetched}")
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_approval.py",
            "status": "PASS",
            "duration": duration,
            "reason": "Pending action creation and status updates verified successfully on approval repository."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_approval.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Approval test failed: {e}"
        }
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                pass
        # Clean up journal file if created
        journal = Path("test_appr_db.sqlite-journal")
        if journal.exists():
            try:
                journal.unlink()
            except Exception:
                pass
