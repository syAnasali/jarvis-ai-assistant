"""Script to run repeatable local agent latency diagnostics and benchmarks."""

import sys
import time
from datetime import datetime, timezone
from app.core.application import Application
from app.agent.models import AgentRequest


def print_iteration_metrics(iter_metrics) -> None:
    """Helper to display metrics for an agent iteration."""
    model_m = iter_metrics.model_metrics
    print(f"  Iteration {iter_metrics.iteration}:")
    print(f"    Iteration Duration: {iter_metrics.duration_ms:.2f} ms")
    print(f"    Tool Calls In Turn: {iter_metrics.tool_calls_count}")
    if model_m:
        print(f"    Model Provider:     {model_m.provider}")
        print(f"    Model Name:         {model_m.model}")
        print(f"    Profile Used:       {model_m.generation_profile}")
        print(f"    Provider Total:     {model_m.total_duration_ms} ms")
        print(f"    Load Duration:      {model_m.load_duration_ms} ms")
        print(f"    Prompt Eval:        {model_m.prompt_eval_duration_ms} ms")
        print(f"    Generation:         {model_m.generation_duration_ms} ms")
        print(f"    Prompt Tokens:      {model_m.prompt_tokens}")
        print(f"    Generated Tokens:   {model_m.generated_tokens}")
        print(f"    Tokens Per Second:  {model_m.tokens_per_second}")
    else:
        print("    Model Metrics:      Not Available")
    print()


def main():
    """Runs local diagnostic benchmarks on the agent loop."""
    print("=" * 60)
    print("Local Diagnostic Benchmark")
    print("=" * 60)
    print("Initializing Jarvis AI Assistant application abstractions...")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        sys.exit(1)

    controller = app.container.get("controller")
    prompts = [
        "Respond with exactly: OK",
        "What is the current local time?",
        "Tell me basic information about this computer's operating system."
    ]

    results = []

    for i, prompt in enumerate(prompts, 1):
        controller.reset()
        print("\n" + "-" * 60)
        print(f"Benchmark Prompt {i}: '{prompt}'")
        print("-" * 60)
        
        request = AgentRequest(
            request_id=f"bench_req_{i}",
            text=prompt,
            source="benchmark",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        start_time = time.perf_counter()
        try:
            response = controller.process_request(request)
            total_duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract metrics from response metadata
            exec_metrics = response.metadata.get("execution_metrics")
            
            print(f"Final Response:\n{response.text}\n")
            print(f"Total Duration:   {total_duration_ms:.2f} ms")
            
            if exec_metrics:
                print(f"Agent Iterations: {exec_metrics.iterations}")
                print(f"Model Calls:      {exec_metrics.model_calls}")
                print(f"Tool Calls:       {exec_metrics.tool_calls}")
                print("\nPer-Iteration Metrics:")
                for im in exec_metrics.iteration_metrics:
                    print_iteration_metrics(im)
                
                # Sum generated tokens across all iterations
                total_gen_tokens = 0
                for im in exec_metrics.iteration_metrics:
                    if im.model_metrics and im.model_metrics.generated_tokens is not None:
                        total_gen_tokens += im.model_metrics.generated_tokens
                
                avg_tokens_per_call = (
                    total_gen_tokens / exec_metrics.model_calls 
                    if exec_metrics.model_calls > 0 else 0
                )

                results.append({
                    "prompt": prompt,
                    "duration_ms": total_duration_ms,
                    "iterations": exec_metrics.iterations,
                    "model_calls": exec_metrics.model_calls,
                    "tool_calls": exec_metrics.tool_calls,
                    "total_gen_tokens": total_gen_tokens,
                    "avg_tokens_per_call": avg_tokens_per_call
                })
            else:
                print("Execution Metrics: Not available (Executor fallback used)")
                results.append({
                    "prompt": prompt,
                    "duration_ms": total_duration_ms,
                    "iterations": 1,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "total_gen_tokens": 0,
                    "avg_tokens_per_call": 0.0
                })
        except Exception as e:
            print(f"Benchmark run failed: {e}")

    print("\n" + "=" * 105)
    print("Benchmark Summary")
    print("=" * 105)
    print(
        f"{'Prompt':<45} | "
        f"{'Duration (ms)':<15} | "
        f"{'Tokens':<8} | "
        f"{'Calls':<6} | "
        f"{'Tools':<6} | "
        f"{'Avg Tokens/Call':<15}"
    )
    print("-" * 105)
    for res in results:
        print(
            f"{res['prompt'][:43]:<45} | "
            f"{res['duration_ms']:<15.2f} | "
            f"{res['total_gen_tokens']:<8} | "
            f"{res['model_calls']:<6} | "
            f"{res['tool_calls']:<6} | "
            f"{res['avg_tokens_per_call']:<15.2f}"
        )
    print("\nNote: These results are local diagnostic metrics and are not scientifically rigorous.\n")


if __name__ == "__main__":
    main()
