"""Unit tests for the MemoryWriteCoordinator class."""

import pytest
import time
import threading
from unittest.mock import MagicMock
from app.memory.models import MemoryWriteResult
from app.memory.write_service import MemoryWriteService
from app.memory.coordinator import MemoryWriteCoordinator


def test_coordinator_asynchronous_execution():
    """Verify that submit returns immediately without waiting for slow write completion."""
    mock_service = MagicMock(spec=MemoryWriteService)
    
    # Event to control execution speed of memory write
    write_started = threading.Event()
    let_write_complete = threading.Event()
    
    def slow_write(text):
        write_started.set()
        let_write_complete.wait()
        return MemoryWriteResult(0, 0, 0, 0, ())

    mock_service.write_memories.side_effect = slow_write
    coordinator = MemoryWriteCoordinator(mock_service, max_pending=4)

    # Submit job
    start_time = time.perf_counter()
    submitted = coordinator.submit("User query")
    duration = time.perf_counter() - start_time
    
    assert submitted is True
    # Should return immediately (well under 50ms)
    assert duration < 0.05
    
    # Wait for background task to start executing
    write_started.wait()
    
    # Let it finish
    let_write_complete.set()
    coordinator.flush()
    coordinator.shutdown()


def test_coordinator_successful_job_metrics():
    """Verify that metrics increment properly upon successful job completion."""
    mock_service = MagicMock(spec=MemoryWriteService)
    mock_service.write_memories.return_value = MemoryWriteResult(3, 2, 0, 1, ("m_1", "m_2"), 15.0)

    coordinator = MemoryWriteCoordinator(mock_service)
    coordinator.submit("Explicit request")
    coordinator.flush()

    metrics = coordinator.get_metrics()
    assert metrics["submitted_jobs"] == 1
    assert metrics["completed_jobs"] == 1
    assert metrics["failed_jobs"] == 0
    assert metrics["skipped_jobs"] == 0
    assert metrics["pending_jobs"] == 0

    coordinator.shutdown()


def test_coordinator_failed_job_isolation():
    """Verify that a database write failure is isolated and does not crash the coordinator."""
    mock_service = MagicMock(spec=MemoryWriteService)
    mock_service.write_memories.side_effect = RuntimeError("SQLite database locked")

    coordinator = MemoryWriteCoordinator(mock_service)
    coordinator.submit("User request")
    coordinator.flush()

    metrics = coordinator.get_metrics()
    assert metrics["submitted_jobs"] == 1
    assert metrics["completed_jobs"] == 0
    assert metrics["failed_jobs"] == 1
    assert metrics["skipped_jobs"] == 0
    
    coordinator.shutdown()


def test_coordinator_bounded_capacity():
    """Verify that queue saturation rejects new submissions without blocking."""
    mock_service = MagicMock(spec=MemoryWriteService)
    
    let_jobs_finish = threading.Event()
    def slow_write(text):
        let_jobs_finish.wait()
        return MemoryWriteResult(1, 1, 0, 0, ("m_1",))

    mock_service.write_memories.side_effect = slow_write
    
    # Bounded capacity of 2
    coordinator = MemoryWriteCoordinator(mock_service, max_pending=2)

    # Submit 2 jobs (exhausts capacity since they wait on event)
    coordinator.submit("Query 1")
    coordinator.submit("Query 2")

    # This third job should exceed capacity and be skipped immediately
    submitted_3 = coordinator.submit("Query 3")
    assert submitted_3 is False

    metrics = coordinator.get_metrics()
    assert metrics["skipped_jobs"] == 1
    assert metrics["submitted_jobs"] == 2
    assert metrics["pending_jobs"] == 2

    # Release background tasks
    let_jobs_finish.set()
    coordinator.flush()
    coordinator.shutdown()


def test_coordinator_shutdown_and_idempotency():
    """Verify that coordinator shutdown flushes accepted jobs and rejects subsequent submissions."""
    mock_service = MagicMock(spec=MemoryWriteService)
    mock_service.write_memories.return_value = MemoryWriteResult(1, 1, 0, 0, ("m_1",))

    coordinator = MemoryWriteCoordinator(mock_service)
    coordinator.submit("Query")
    
    coordinator.shutdown()
    
    # Metric should reflect completion
    assert coordinator.get_metrics()["completed_jobs"] == 1
    
    # Idempotent shutdown calls should work without errors
    coordinator.shutdown()

    # Submissions after shutdown must be rejected
    submitted = coordinator.submit("Query after shutdown")
    assert submitted is False
