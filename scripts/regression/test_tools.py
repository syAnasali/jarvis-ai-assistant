import time
from app.tools.registry import ToolRegistry
from app.tools.executor import ToolExecutor, ToolCall
from app.tools.builtin.system import CurrentTimeTool

def run_regression() -> dict:
    start_time = time.perf_counter()
    try:
        registry = ToolRegistry()
        time_tool = CurrentTimeTool()
        registry.register(time_tool)
        
        # Verify registered
        if not registry.has("get_current_time"):
            raise ValueError("ToolRegistry is missing get_current_time tool")
            
        executor = ToolExecutor(registry)
        tc = ToolCall(tool_name="get_current_time", arguments={})
        result = executor.execute(tc)
        
        if not result.success or "iso_datetime" not in result.output:
            raise ValueError(f"Tool execution output mismatch. Result: {result}")
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_tools.py",
            "status": "PASS",
            "duration": duration,
            "reason": "Successfully registered and executed get_current_time tool."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_tools.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Tools test failed: {e}"
        }
