"""Diagnostic script demonstrating foreground priority latency ordering."""

import threading
import time
from app.ai.scheduler import PriorityInferenceScheduler, InferencePriority


def run_latency_diagnostic():
    print("==========================================================")
    print("RUNNING FOREGROUND PRIORITY LATENCY DIAGNOSTIC")
    print("==========================================================")

    scheduler = PriorityInferenceScheduler()
    scheduler.start()

    execution_order = []
    active_block_event = threading.Event()
    active_started_event = threading.Event()

    # Time measurements
    times = {}

    def make_op(name, is_blocking=False):
        def op():
            if is_blocking:
                active_started_event.set()
                active_block_event.wait()
            else:
                time.sleep(0.02)
            execution_order.append(name)
            times[name] = time.perf_counter()
            return name
        return op

    # 1. Start active background inference
    print("1. Submitting active background job...")
    f_active = scheduler.submit(
        make_op("active_background", is_blocking=True),
        priority=InferencePriority.MEMORY_EXTRACTION
    )

    # Wait for active job to start running
    assert active_started_event.wait(timeout=2.0)
    t_start = time.perf_counter()

    # 2. Queue another background job, and then a foreground job
    print("2. Queuing queued_background...")
    f_bg = scheduler.submit(
        make_op("queued_background"),
        priority=InferencePriority.MEMORY_EXTRACTION
    )

    print("3. Queuing queued_foreground...")
    f_fg = scheduler.submit(
        make_op("queued_foreground"),
        priority=InferencePriority.FOREGROUND
    )

    # 3. Release active job
    print("4. Releasing active job barrier...")
    active_block_event.set()

    # 4. Wait for completion
    f_active.result()
    f_fg.result()
    f_bg.result()

    scheduler.shutdown()

    # Calculate latency timings
    active_duration_ms = (times["active_background"] - t_start) * 1000
    fg_wait_ms = (times["queued_foreground"] - times["active_background"]) * 1000
    bg_wait_ms = (times["queued_background"] - times["queued_foreground"]) * 1000

    print("\nMeasurements:")
    print(f"Active background duration: {active_duration_ms:.2f} ms")
    print(f"Foreground queue wait:      {fg_wait_ms:.2f} ms")
    print(f"Queued background wait:     {bg_wait_ms:.2f} ms")
    print(f"Execution Order:            {' -> '.join(execution_order)}")

    # Assertions
    is_fg_first = execution_order == ["active_background", "queued_foreground", "queued_background"]
    is_not_preempted = execution_order[0] == "active_background"
    is_ordered = execution_order[1:3] == ["queued_foreground", "queued_background"]

    print("\n----------------------------------------------------------")
    print("Foreground Priority Latency Diagnostic Summary:")
    print(f"Foreground selected before queued background: {'PASS' if is_fg_first else 'FAIL'}")
    print(f"Active background preempted:                  {'NO' if is_not_preempted else 'YES'}")
    print(f"Scheduler queue ordering:                     {'PASS' if is_ordered else 'FAIL'}")
    print("==========================================================")


if __name__ == "__main__":
    run_latency_diagnostic()
