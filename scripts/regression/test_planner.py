import time
from datetime import datetime, timezone
from app.agent.models import AgentRequest
from app.planning.router import ExecutionRouter
from app.planning.models import ExecutionMode

def run_regression() -> dict:
    start_time = time.perf_counter()
    try:
        router = ExecutionRouter()
        
        # Verify direct classification for simple request
        req1 = AgentRequest(
            request_id="req_simple",
            text="what is the time?",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        decision1 = router.route(req1)
        if decision1.mode != ExecutionMode.DIRECT:
            raise ValueError(f"Simple query expected DIRECT mode, got: {decision1.mode.name}")
            
        # Verify planned classification for complex multi-action request
        req2 = AgentRequest(
            request_id="req_complex",
            text="Create notes.txt on desktop then analyze results and summarize them",
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        decision2 = router.route(req2)
        if decision2.mode != ExecutionMode.PLANNED:
            raise ValueError(f"Multi-step query expected PLANNED mode, got: {decision2.mode.name}")
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_planner.py",
            "status": "PASS",
            "duration": duration,
            "reason": "Router successfully verified DIRECT and PLANNED heuristics classification."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_planner.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Planner test failed: {e}"
        }
