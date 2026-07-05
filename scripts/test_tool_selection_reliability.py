"""Script to run repeatable agent tool-selection reliability diagnostics."""

import sys
import time
from datetime import datetime, timezone
from app.core.application import Application
from app.agent.models import AgentRequest


def run_prompt_test(controller, prompt: str, expected_tool: str | None, run_num: int) -> dict:
    """Runs a single prompt diagnostic turn with a fresh context."""
    # Reset controller to clear conversation history before each run
    controller.reset()

    request = AgentRequest(
        request_id=f"rel_req_{run_num}_{int(time.time())}",
        text=prompt,
        source="reliability_test",
        timestamp=datetime.now(timezone.utc),
        metadata={}
    )

    start_time = time.perf_counter()
    try:
        response = controller.process_request(request)
        total_duration_ms = (time.perf_counter() - start_time) * 1000
        
        exec_metrics = response.metadata.get("execution_metrics")
        requested_tools = exec_metrics.requested_tools if exec_metrics else ()
        
        # Determine success
        if expected_tool is None:
            success = len(requested_tools) == 0
        else:
            success = expected_tool in requested_tools

        print(f"Prompt:          '{prompt}'")
        print(f"Run:             {run_num}")
        print(f"Selected Tools:  {requested_tools if requested_tools else 'none'}")
        print(f"Tool Call Count: {exec_metrics.tool_calls if exec_metrics else 0}")
        print(f"Model Calls:     {exec_metrics.model_calls if exec_metrics else 1}")
        print(f"Iterations:      {exec_metrics.iterations if exec_metrics else 1}")
        print(f"Final Response:  {response.text.strip()}")
        print(f"Duration:        {total_duration_ms:.2f} ms")
        print()

        return {
            "success": success,
            "requested_tools": requested_tools,
            "model_calls": exec_metrics.model_calls if exec_metrics else 1,
            "iterations": exec_metrics.iterations if exec_metrics else 1,
            "tool_calls": exec_metrics.tool_calls if exec_metrics else 0,
            "duration_ms": total_duration_ms
        }
    except Exception as e:
        print(f"Error executing run {run_num}: {e}")
        return {
            "success": False,
            "requested_tools": (),
            "model_calls": 0,
            "iterations": 0,
            "tool_calls": 0,
            "duration_ms": 0.0
        }


def main() -> int:
    """Executes the reliability diagnostics suite."""
    print("=" * 60)
    print("Tool Selection Reliability Diagnostic")
    print("=" * 60)
    print("Initializing Jarvis AI Assistant application abstractions...")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return 1

    controller = app.container.get("controller")
    
    # Define suite of prompts
    test_cases = [
        {"prompt": "What is the current local time?", "expected": "get_current_time"},
        {"prompt": "Tell me basic information about this computer's operating system.", "expected": "get_system_info"},
        {"prompt": "What Python runtime version is this assistant currently running on?", "expected": "get_system_info"},
        {"prompt": "Explain what an operating system is in one sentence.", "expected": None},
        {"prompt": "Why do computer clocks sometimes drift?", "expected": None},
        {"prompt": "Explain Python recursion in one sentence.", "expected": None}
    ]

    runs_per_case = 3
    results_map = {}

    for case in test_cases:
        prompt = case["prompt"]
        expected = case["expected"]
        results_map[prompt] = []
        
        print("-" * 60)
        print(f"Diagnostic Category: '{prompt}' (Expected Tool: {expected})")
        print("-" * 60)
        
        for run in range(1, runs_per_case + 1):
            res = run_prompt_test(controller, prompt, expected, run)
            results_map[prompt].append(res)

    # Calculate summary metrics
    print("=" * 60)
    print("Diagnostic Summary")
    print("=" * 60)
    
    total_tool_prompts_runs = 0
    successful_tool_selection_runs = 0
    total_no_tool_runs = 0
    false_positives = 0

    print(f"{'Expected Tool':<20} | {'Successes':<10} | {'Total Runs':<10} | {'Reliability (%)':<15}")
    print("-" * 63)

    for case in test_cases:
        prompt = case["prompt"]
        expected = case["expected"]
        runs = results_map[prompt]
        
        successes = sum(1 for r in runs if r["success"])
        total_runs = len(runs)
        reliability = (successes / total_runs) * 100.0
        
        lbl = expected if expected else "none"
        print(f"{lbl:<20} | {successes:<10} | {total_runs:<10} | {reliability:<15.1f}%")
        
        if expected is not None:
            total_tool_prompts_runs += total_runs
            successful_tool_selection_runs += successes
        else:
            total_no_tool_runs += total_runs
            # A false positive is a case where expected is None but tool calls were made
            false_positives += sum(1 for r in runs if len(r["requested_tools"]) > 0)

    overall_tool_reliability = (
        (successful_tool_selection_runs / total_tool_prompts_runs) * 100.0 
        if total_tool_prompts_runs > 0 else 0.0
    )

    print("-" * 63)
    print(f"Overall Tool-Selection Reliability: {overall_tool_reliability:.1f}%")
    print(f"False-Positive Tool Calls:           {false_positives} (out of {total_no_tool_runs} no-tool runs)")
    print("=" * 60)
    print("Diagnostic Suite Complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
