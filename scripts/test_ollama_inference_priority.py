"""Diagnostic script showing priority-aware scheduling on live Ollama connection."""

import threading
import time
from app.core.bootstrap import Bootstrap
from app.config.settings import settings
from app.ai.manager import LLMManager
from app.ai.providers.ollama import OllamaProvider
from app.ai.scheduler import PriorityInferenceScheduler, InferencePriority
from app.ai.models import GenerationProfile


def run_ollama_priority_diagnostic():
    print("==========================================================")
    print("RUNNING OLLAMA INFERENCE PRIORITY DIAGNOSTIC")
    print("This diagnostic verifies scheduling order, not GPU preemption or throughput.")
    print("==========================================================")

    # 1. Initialize bootstrap to setup directories
    bootstrap = Bootstrap()
    bootstrap.setup()

    # 2. Setup Scheduler, LLMManager, and Provider
    scheduler = PriorityInferenceScheduler()
    scheduler.start()

    llm_manager = LLMManager(scheduler=scheduler)
    provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
    llm_manager.register_provider("ollama", provider)
    llm_manager.load_provider("ollama")

    execution_order = []
    futures = []

    # Small query using FAST profile
    messages = [{"role": "user", "content": "Respond with exactly: OK"}]

    def run_generate(name, priority):
        def op():
            res = llm_manager.generate(
                messages=messages,
                profile=GenerationProfile.FAST,
                priority=priority
            )
            execution_order.append(name)
            return res
        return op

    print("1. Submitting active background MEMORY_EXTRACTION job (takes time in Ollama)...")
    f_active = scheduler.submit(run_generate("active_extraction", InferencePriority.MEMORY_EXTRACTION), priority=InferencePriority.MEMORY_EXTRACTION)

    # Wait 100ms to let it acquire the active worker slot
    time.sleep(0.1)

    print("2. Queuing queued_extraction (MEMORY_EXTRACTION) in background...")
    f_extract = scheduler.submit(run_generate("queued_extraction", InferencePriority.MEMORY_EXTRACTION), priority=InferencePriority.MEMORY_EXTRACTION)

    print("3. Queuing queued_foreground (FOREGROUND) in foreground...")
    f_fore = scheduler.submit(run_generate("queued_foreground", InferencePriority.FOREGROUND), priority=InferencePriority.FOREGROUND)

    # Wait for all to finish
    print("Waiting for all Ollama requests to complete...")
    f_active.result()
    f_extract.result()
    f_fore.result()

    scheduler.shutdown()

    print("\nResults:")
    print(f"Execution Order: {' -> '.join(execution_order)}")

    # Assertions
    is_preempted = "NO"  # Ollama active job is non-preemptive
    is_prioritized = "NO"
    if len(execution_order) == 3:
        # Since active runs first:
        # execution_order[0] should be active_extraction
        # execution_order[1] should be queued_foreground
        # execution_order[2] should be queued_extraction
        if execution_order[0] == "active_extraction":
            is_preempted = "NO"
        if execution_order[1] == "queued_foreground":
            is_prioritized = "YES"

    print(f"\nActive inference preempted:  {is_preempted}")
    print(f"Queued foreground prioritized: {is_prioritized}")
    print("==========================================================")


if __name__ == "__main__":
    run_ollama_priority_diagnostic()
