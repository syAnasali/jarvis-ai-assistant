#!/usr/bin/env python3
"""Performance & Latency Benchmark Validation Suite for Jarvis AI Assistant.

Measures startup, time-to-first-token, response latency, tool execution latency,
memory retrieval latency, conversation persistence latency, prompt construction latency,
and scheduler latency.
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from app.core.application import Application
from app.agent.models import AgentRequest, ToolCall
from app.ai.models import GenerationResult, GenerationMetrics
from app.agent.messages import Message, MessageRole


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def setup_test_app():
    app = Application()
    app.initialize()
    try:
        app._initialize_llm()
    except Exception:
        from app.ai.manager import LLMManager
        llm_manager = LLMManager()
        mock_provider = MagicMock()
        mock_provider.initialize.return_value = None
        llm_manager.register_provider("mock", mock_provider)
        llm_manager.switch_provider("mock")
        app.container.register("llm_manager", llm_manager)
    app._initialize_agent()
    return app


def benchmark_startup_time() -> float:
    start_time = time.perf_counter()
    app = setup_test_app()
    duration_ms = (time.perf_counter() - start_time) * 1000
    app.shutdown()
    safe_print(f"Benchmark Startup Time:                  {duration_ms:.2f} ms")
    return duration_ms


def benchmark_first_token_latency() -> float:
    app = setup_test_app()
    controller = app.container.get("controller")

    mock_provider = MagicMock()
    mock_provider.generate_stream.return_value = iter([{"message": {"content": "Token1 "}}, {"message": {"content": "Token2"}}])
    mock_provider.initialize.return_value = None
    mock_provider.shutdown.return_value = None

    llm_mgr = app.container.get("llm_manager")
    llm_mgr.register_provider("bench_mock", mock_provider)
    llm_mgr.switch_provider("bench_mock")

    req = AgentRequest(request_id="req_bench_ft", text="Stream response", source="test")
    
    start_time = time.perf_counter()
    stream = controller.process_request_stream(req)
    st_iter = iter(stream)
    first_chunk = next(st_iter)  # Fetch first chunk
    first_token_ms = (time.perf_counter() - start_time) * 1000

    # Consume remaining chunks to let stream finish & save message
    for _ in st_iter:
        pass

    safe_print(f"Benchmark First Token Latency:           {first_token_ms:.2f} ms")
    app.shutdown()
    return first_token_ms


def benchmark_average_response_latency() -> float:
    app = setup_test_app()
    controller = app.container.get("controller")

    raw_resp = {"message": {"role": "assistant", "content": "Benchmark response."}}
    app.container.get("llm_manager").generate = MagicMock(return_value=GenerationResult(
        raw_response=raw_resp,
        metrics=GenerationMetrics(provider="mock", model="mock")
    ))

    latencies = []
    for i in range(5):
        t0 = time.perf_counter()
        req = AgentRequest(request_id=f"req_bench_resp_{i}", text=f"Bench request {i}", source="test")
        controller.process_request(req)
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_ms = sum(latencies) / len(latencies)
    safe_print(f"Benchmark Average Response Latency:      {avg_ms:.2f} ms")
    app.shutdown()
    return avg_ms


def benchmark_tool_execution_latency() -> float:
    app = setup_test_app()
    executor = app.container.get("tool_executor")

    tool_call = ToolCall(tool_name="get_current_time", arguments={})

    t0 = time.perf_counter()
    for _ in range(10):
        executor.execute(tool_call)
    avg_ms = ((time.perf_counter() - t0) * 1000) / 10.0

    safe_print(f"Benchmark Tool Execution Latency:        {avg_ms:.2f} ms")
    app.shutdown()
    return avg_ms


def benchmark_memory_retrieval_latency() -> float:
    app = setup_test_app()
    retriever = app.container.get("memory_retriever")

    t0 = time.perf_counter()
    for _ in range(10):
        retriever.retrieve("test user query memory")
    avg_ms = ((time.perf_counter() - t0) * 1000) / 10.0

    safe_print(f"Benchmark Memory Retrieval Latency:      {avg_ms:.2f} ms")
    app.shutdown()
    return avg_ms


def benchmark_conversation_persistence_latency() -> float:
    app = setup_test_app()
    from app.utils.id_generator import generate_message_id
    conv_mgr = app.container.get("conversation_manager")
    session = conv_mgr.create_session()

    t0 = time.perf_counter()
    for i in range(10):
        conv_mgr.add_message(session.session_id, Message(id=generate_message_id(), role=MessageRole.USER, content=f"Persist msg {i}"))
    avg_ms = ((time.perf_counter() - t0) * 1000) / 10.0

    safe_print(f"Benchmark Conversation Persistence Latency:{avg_ms:.2f} ms/msg")
    app.shutdown()
    return avg_ms


def benchmark_prompt_construction_latency() -> float:
    app = setup_test_app()
    controller = app.container.get("controller")

    req = AgentRequest(request_id="req_bench_prompt", text="Benchmark prompt construction", source="test")
    
    t0 = time.perf_counter()
    controller._prepare_request(req)
    duration_ms = (time.perf_counter() - t0) * 1000

    safe_print(f"Benchmark Prompt Construction Latency:   {duration_ms:.2f} ms")
    app.shutdown()
    return duration_ms


def benchmark_scheduler_latency() -> float:
    app = setup_test_app()
    scheduler = app.container.get("inference_scheduler")

    t0 = time.perf_counter()
    res = scheduler.execute(lambda: "scheduler test result")
    duration_ms = (time.perf_counter() - t0) * 1000

    assert res == "scheduler test result"
    safe_print(f"Benchmark Scheduler Dispatch Latency:    {duration_ms:.2f} ms")
    app.shutdown()
    return duration_ms


def run_all_performance_benchmarks():
    safe_print("============================================================")
    safe_print("STARTING PERFORMANCE & LATENCY BENCHMARK SUITE")
    safe_print("============================================================")

    results = {
        "startup_ms": benchmark_startup_time(),
        "first_token_ms": benchmark_first_token_latency(),
        "avg_response_ms": benchmark_average_response_latency(),
        "tool_execution_ms": benchmark_tool_execution_latency(),
        "memory_retrieval_ms": benchmark_memory_retrieval_latency(),
        "conversation_persistence_ms": benchmark_conversation_persistence_latency(),
        "prompt_construction_ms": benchmark_prompt_construction_latency(),
        "scheduler_dispatch_ms": benchmark_scheduler_latency()
    }

    safe_print("\n============================================================")
    safe_print("ALL PERFORMANCE BENCHMARKS COMPLETED SUCCESSFULLY!")
    safe_print("============================================================")
    return results


if __name__ == "__main__":
    run_all_performance_benchmarks()
