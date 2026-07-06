"""Unit tests for PriorityInferenceScheduler."""

import pytest
import threading
import time
from concurrent.futures import Future

from app.ai.scheduler import (
    InferencePriority,
    PriorityInferenceScheduler,
    SchedulerState,
)


def test_scheduler_executes_operation():
    """Verify scheduler executes a simple operation and returns the result."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        res = scheduler.execute(lambda: 42, priority=InferencePriority.FOREGROUND)
        assert res == 42
    finally:
        scheduler.shutdown()


def test_scheduler_propagates_exception():
    """Verify scheduler propagates exceptions raised by operations."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        with pytest.raises(ValueError, match="Test error"):
            scheduler.execute(lambda: (_ for _ in ()).throw(ValueError("Test error")))
    finally:
        scheduler.shutdown()


def test_single_worker_serializes_execution():
    """Verify scheduler worker runs only one job at a time."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        active_jobs = 0
        max_concurrent = 0
        lock = threading.Lock()

        def block_job():
            nonlocal active_jobs, max_concurrent
            with lock:
                active_jobs += 1
                if active_jobs > max_concurrent:
                    max_concurrent = active_jobs
            time.sleep(0.05)
            with lock:
                active_jobs -= 1
            return True

        f1 = scheduler.submit(block_job, priority=InferencePriority.FOREGROUND)
        f2 = scheduler.submit(block_job, priority=InferencePriority.FOREGROUND)
        f3 = scheduler.submit(block_job, priority=InferencePriority.FOREGROUND)

        f1.result()
        f2.result()
        f3.result()

        assert max_concurrent == 1
    finally:
        scheduler.shutdown()


def test_priority_queue_ordering():
    """Verify queued jobs are executed in explicit priority order: FOREGROUND > MEMORY_RESOLUTION > MEMORY_EXTRACTION."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        execution_order = []
        barrier_event = threading.Event()
        start_event = threading.Event()

        # Step 1: Submit blocking job so worker is occupied
        def blocking_job():
            start_event.set()
            barrier_event.wait()

        scheduler.submit(blocking_job, priority=InferencePriority.FOREGROUND)

        # Wait until block job starts executing
        assert start_event.wait(timeout=2.0)

        # Step 2: Queue other jobs with different priorities
        def make_job(name):
            return lambda: execution_order.append(name)

        # Submit out of order
        scheduler.submit(make_job("extraction"), priority=InferencePriority.MEMORY_EXTRACTION)
        scheduler.submit(make_job("resolution"), priority=InferencePriority.MEMORY_RESOLUTION)
        scheduler.submit(make_job("foreground"), priority=InferencePriority.FOREGROUND)

        # Step 3: Release block
        barrier_event.set()

        # Wait for all jobs to complete
        time.sleep(0.1)

        # Expected execution order after the active job: foreground > resolution > extraction
        assert execution_order == ["foreground", "resolution", "extraction"]
    finally:
        scheduler.shutdown()


def test_fifo_preservation_within_same_priority():
    """Verify jobs with identical priority execute in FIFO submission order."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        execution_order = []
        barrier_event = threading.Event()
        start_event = threading.Event()

        # Blocking job
        scheduler.submit(lambda: (start_event.set(), barrier_event.wait()), priority=InferencePriority.FOREGROUND)
        assert start_event.wait(timeout=2.0)

        # Submit multiple jobs of same priority
        scheduler.submit(lambda: execution_order.append("A"), priority=InferencePriority.FOREGROUND)
        scheduler.submit(lambda: execution_order.append("B"), priority=InferencePriority.FOREGROUND)
        scheduler.submit(lambda: execution_order.append("C"), priority=InferencePriority.FOREGROUND)

        barrier_event.set()
        time.sleep(0.1)

        assert execution_order == ["A", "B", "C"]
    finally:
        scheduler.shutdown()


def test_currently_executing_job_not_preempted():
    """Verify that a lower-priority job currently running is not interrupted by a higher-priority one."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        execution_order = []
        barrier_event = threading.Event()
        start_event = threading.Event()

        # Submit a low-priority extraction job that blocks
        scheduler.submit(lambda: (start_event.set(), barrier_event.wait(), execution_order.append("extraction")), priority=InferencePriority.MEMORY_EXTRACTION)
        assert start_event.wait(timeout=2.0)

        # Submit a high-priority foreground job
        scheduler.submit(lambda: execution_order.append("foreground"), priority=InferencePriority.FOREGROUND)

        # Release barrier
        barrier_event.set()
        time.sleep(0.1)

        # The active extraction job should complete before the queued foreground job starts
        assert execution_order == ["extraction", "foreground"]
    finally:
        scheduler.shutdown()


def test_worker_survives_failed_operations():
    """Verify worker continues executing subsequent jobs even if some operations fail."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        f1 = scheduler.submit(lambda: (_ for _ in ()).throw(RuntimeError("Fail")), priority=InferencePriority.FOREGROUND)
        f2 = scheduler.submit(lambda: 100, priority=InferencePriority.FOREGROUND)

        with pytest.raises(RuntimeError):
            f1.result()
        assert f2.result() == 100
    finally:
        scheduler.shutdown()


def test_submission_after_shutdown_rejected():
    """Verify enqueuing jobs after scheduler shutdown is rejected."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    scheduler.shutdown()

    with pytest.raises(RuntimeError, match="Scheduler is not running"):
        scheduler.submit(lambda: 42)


def test_shutdown_waits_for_queued_jobs():
    """Verify shutdown does not abandon queued jobs."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    execution_order = []

    # Queue several jobs
    scheduler.submit(lambda: (time.sleep(0.02), execution_order.append("A")), priority=InferencePriority.FOREGROUND)
    scheduler.submit(lambda: execution_order.append("B"), priority=InferencePriority.FOREGROUND)

    # Initiate shutdown (should block until B completes)
    scheduler.shutdown()

    assert execution_order == ["A", "B"]


def test_shutdown_idempotent():
    """Verify shutdown can be called multiple times safely."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    scheduler.shutdown()
    scheduler.shutdown()
    assert scheduler._state == SchedulerState.STOPPED


def test_scheduler_metrics():
    """Verify metrics tracking counts successful/failed jobs and queue depth."""
    scheduler = PriorityInferenceScheduler()
    scheduler.start()
    try:
        f1 = scheduler.submit(lambda: 42, priority=InferencePriority.FOREGROUND)
        f2 = scheduler.submit(lambda: (_ for _ in ()).throw(ValueError("Fail")), priority=InferencePriority.MEMORY_EXTRACTION)

        f1.result()
        with pytest.raises(ValueError):
            f2.result()

        metrics = scheduler.get_metrics()
        assert metrics["submitted_jobs"] == 2
        assert metrics["completed_jobs"] == 2
        assert metrics["failed_jobs"] == 1
        assert metrics["foreground_jobs"] == 1
        assert metrics["memory_extraction_jobs"] == 1
        assert metrics["max_observed_queue_depth"] >= 1
    finally:
        scheduler.shutdown()
