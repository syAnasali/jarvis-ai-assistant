"""Priority-aware local model inference scheduler."""

import queue
import threading
import time
import itertools
from enum import IntEnum, Enum
from dataclasses import dataclass, field
from typing import Callable, Any, Dict
from concurrent.futures import Future


class InferencePriority(IntEnum):
    """Priority levels for local model inference scheduling.

    Lower numeric values represent higher priority.
    """
    FOREGROUND = 0
    MEMORY_RESOLUTION = 10
    MEMORY_EXTRACTION = 20
    POISON_PILL = 999  # Internal lowest-priority shutdown signal


class SchedulerState(Enum):
    """Lifecycle states of the PriorityInferenceScheduler."""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class InferenceJob:
    """An immutable, scheduler-internal representation of a queued inference job."""
    job_id: str
    priority: InferencePriority
    sequence_number: int
    operation: Callable[[], Any]
    future: Future = field(compare=False)
    submitted_at: float

    def __lt__(self, other: "InferenceJob") -> bool:
        if not isinstance(other, InferenceJob):
            return NotImplemented
        # Primary key: priority. Secondary key: sequence_number (ensuring deterministic FIFO)
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.sequence_number < other.sequence_number


@dataclass
class SchedulerMetrics:
    """Metrics tracking for PriorityInferenceScheduler."""
    submitted_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    foreground_jobs: int = 0
    memory_resolution_jobs: int = 0
    memory_extraction_jobs: int = 0
    max_observed_queue_depth: int = 0
    total_wait_time_ms: float = 0.0


class PriorityInferenceScheduler:
    """Serializes inference operations on local LLM runtimes, ordering them by priority."""

    def __init__(self) -> None:
        """Initializes the PriorityInferenceScheduler."""
        self._queue: queue.PriorityQueue[InferenceJob] = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._state = SchedulerState.CREATED
        self._job_id_counter = itertools.count(1)
        self._seq_counter = itertools.count(1)
        self._metrics = SchedulerMetrics()

        # Dedicated worker thread
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="inference_scheduler_worker",
            daemon=True
        )

    def start(self) -> None:
        """Starts the background worker thread. Idempotent."""
        with self._lock:
            if self._state == SchedulerState.RUNNING:
                return
            if self._state in (SchedulerState.STOPPING, SchedulerState.STOPPED):
                raise RuntimeError("Cannot start a scheduler that is stopping or stopped.")
            self._state = SchedulerState.RUNNING
            self._worker_thread.start()

    def shutdown(self) -> None:
        """Gracefully shuts down the scheduler, completing all queued jobs."""
        with self._lock:
            if self._state in (SchedulerState.STOPPING, SchedulerState.STOPPED):
                return
            self._state = SchedulerState.STOPPING
            # Queue a poison pill to stop the worker loop after all pending jobs
            # Use Future() and a dummy operation for compatibility
            poison_job = InferenceJob(
                job_id="poison_pill",
                priority=InferencePriority.POISON_PILL,
                sequence_number=next(self._seq_counter),
                operation=lambda: None,
                future=Future(),
                submitted_at=time.perf_counter()
            )
            self._queue.put(poison_job)

        self._worker_thread.join()
        with self._lock:
            self._state = SchedulerState.STOPPED

    def submit(self, operation: Callable[[], Any], priority: InferencePriority = InferencePriority.FOREGROUND) -> Future:
        """Asynchronously enqueues an operation to be run at the specified priority.

        Args:
            operation: A callable executing the inference.
            priority: Scheduling priority for the job.

        Returns:
            Future: A Future resolving to the operation result or raising the exception.
        """
        with self._lock:
            if self._state != SchedulerState.RUNNING:
                raise RuntimeError("Cannot submit job: Scheduler is not running.")

            job_id = f"job_{next(self._job_id_counter)}"
            seq = next(self._seq_counter)
            fut = Future()

            job = InferenceJob(
                job_id=job_id,
                priority=priority,
                sequence_number=seq,
                operation=operation,
                future=fut,
                submitted_at=time.perf_counter()
            )

            # Metrics
            self._metrics.submitted_jobs += 1
            if priority == InferencePriority.FOREGROUND:
                self._metrics.foreground_jobs += 1
            elif priority == InferencePriority.MEMORY_RESOLUTION:
                self._metrics.memory_resolution_jobs += 1
            elif priority == InferencePriority.MEMORY_EXTRACTION:
                self._metrics.memory_extraction_jobs += 1

            self._queue.put(job)

            # Max observed queue depth
            q_size = self._queue.qsize()
            if q_size > self._metrics.max_observed_queue_depth:
                self._metrics.max_observed_queue_depth = q_size

            return fut

    def execute(self, operation: Callable[[], Any], priority: InferencePriority = InferencePriority.FOREGROUND) -> Any:
        """Synchronously submits and executes an operation, blocking until completion.

        Args:
            operation: A callable executing the inference.
            priority: Scheduling priority for the job.

        Returns:
            Any: The successful result of the operation.

        Raises:
            Exception: Re-raises the exception raised by the operation.
        """
        fut = self.submit(operation, priority)
        return fut.result()

    @property
    def worker_thread(self) -> threading.Thread | None:
        """Returns the active scheduler worker thread."""
        return self._worker_thread

    def get_metrics(self) -> Dict[str, Any]:
        """Returns thread-safe scheduler execution metrics."""
        with self._lock:
            completed = self._metrics.completed_jobs
            avg_wait = (self._metrics.total_wait_time_ms / completed) if completed > 0 else 0.0
            return {
                "submitted_jobs": self._metrics.submitted_jobs,
                "completed_jobs": completed,
                "failed_jobs": self._metrics.failed_jobs,
                "foreground_jobs": self._metrics.foreground_jobs,
                "memory_resolution_jobs": self._metrics.memory_resolution_jobs,
                "memory_extraction_jobs": self._metrics.memory_extraction_jobs,
                "current_queue_depth": self._queue.qsize(),
                "max_observed_queue_depth": self._metrics.max_observed_queue_depth,
                "average_queue_wait_ms": avg_wait,
            }

    def _worker_loop(self) -> None:
        """Continuous thread worker execution loop."""
        from app.core.logger import JarvisLogger
        logger = JarvisLogger.get_logger("inference_scheduler")

        while True:
            try:
                job = self._queue.get()
                if job.priority == InferencePriority.POISON_PILL:
                    self._queue.task_done()
                    break

                self._execute_job(job, logger)
                self._queue.task_done()
            except Exception as e:
                logger.critical(f"Unhandled exception in scheduler worker loop: {e}")

    def _execute_job(self, job: InferenceJob, logger: Any) -> None:
        """Executes a single enqueued job, resolving its Future and logging metrics."""
        wait_start = job.submitted_at
        exec_start = time.perf_counter()
        queue_wait_ms = (exec_start - wait_start) * 1000

        success = False
        try:
            result = job.operation()
            job.future.set_result(result)
            success = True
        except Exception as e:
            job.future.set_exception(e)
        finally:
            exec_duration_ms = (time.perf_counter() - exec_start) * 1000
            total_duration_ms = queue_wait_ms + exec_duration_ms

            # Safe metrics capture
            with self._lock:
                self._metrics.completed_jobs += 1
                self._metrics.total_wait_time_ms += queue_wait_ms
                if not success:
                    self._metrics.failed_jobs += 1

            # Safe logging: logs only job stats, NOT model inputs/outputs
            logger.info(
                f"Inference job completed: "
                f"job_id={job.job_id}, "
                f"priority={job.priority.name}, "
                f"queue_wait_ms={queue_wait_ms:.2f}, "
                f"execution_ms={exec_duration_ms:.2f}, "
                f"success={success}, "
                f"queue_depth={self._queue.qsize()}"
            )
