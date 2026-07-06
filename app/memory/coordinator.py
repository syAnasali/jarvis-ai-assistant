"""In-process background coordinator for asynchronous memory writes."""

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Set
from app.core.logger import JarvisLogger
from app.memory.write_service import MemoryWriteService
from app.memory.models import MemoryWriteResult

logger = JarvisLogger.get_logger("memory_coordinator")


class MemoryWriteCoordinator:
    """Orchestrates asynchronous memory extraction and database persistence.

    Uses a single background worker thread to serialize writes to SQLite and prevent blocking
    the user-visible response generation.
    """

    def __init__(self, write_service: MemoryWriteService, max_pending: int = 8) -> None:
        """Initializes the MemoryWriteCoordinator.

        Args:
            write_service: Injected MemoryWriteService instance.
            max_pending: Bounded capacity for the background write queue.
        """
        self._write_service = write_service
        self._max_pending = max_pending
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="memory_worker")
        self._lock = threading.Lock()
        self._active_futures: Set[Future] = set()
        self._is_shutdown = False

        # Metrics
        self._submitted_jobs = 0
        self._completed_jobs = 0
        self._failed_jobs = 0
        self._skipped_jobs = 0

    def submit(self, source_text: str) -> bool:
        """Submits a user request text for background memory processing.

        Args:
            source_text: Raw user request text.

        Returns:
            bool: True if the job was successfully scheduled, False otherwise.
        """
        # Obvious empty/whitespace check
        if not source_text or not source_text.strip():
            return False

        with self._lock:
            if self._is_shutdown:
                logger.warning("MemoryWriteCoordinator is shut down. Rejecting job.")
                return False

            # Clean completed futures to calculate current pending jobs accurately
            self._active_futures = {f for f in self._active_futures if not f.done()}

            # Enforce bounded capacity
            if len(self._active_futures) >= self._max_pending:
                self._skipped_jobs += 1
                logger.warning("MemoryWriteCoordinator pending queue capacity limit reached. Skipping job.")
                return False

            self._submitted_jobs += 1
            # Submit to ThreadPoolExecutor
            future = self._executor.submit(self._write_service.write_memories, source_text)
            self._active_futures.add(future)

        # Add completion callback to update metrics and log results
        future.add_done_callback(self._on_job_complete)
        return True

    def _on_job_complete(self, future: Future) -> None:
        """Completion callback to release references and log metrics/failures."""
        with self._lock:
            self._active_futures.discard(future)

        try:
            res: MemoryWriteResult = future.result()
            with self._lock:
                self._completed_jobs += 1

            logger.info(
                f"Asynchronous memory write complete: "
                f"extracted={res.extracted_count}, "
                f"persisted={res.persisted_count}, "
                f"duplicates={res.duplicate_count}, "
                f"rejected={res.rejected_count}, "
                f"duration_ms={res.duration_ms:.2f}"
            )
        except Exception as e:
            with self._lock:
                self._failed_jobs += 1
            logger.error(
                f"Asynchronous memory write failed: "
                f"type={type(e).__name__}, "
                f"message={str(e)}"
            )

    def flush(self) -> None:
        """Blocks until all currently queued or running memory write tasks complete."""
        with self._lock:
            futures_to_wait = list(self._active_futures)

        if futures_to_wait:
            from concurrent.futures import wait
            wait(futures_to_wait)

    def shutdown(self) -> None:
        """Idempotently shuts down the background worker pool, waiting for pending jobs."""
        with self._lock:
            if self._is_shutdown:
                return
            self._is_shutdown = True

        # shutdown(wait=True) waits for currently running and pending tasks to finish
        self._executor.shutdown(wait=True)
        logger.info("MemoryWriteCoordinator successfully shut down.")

    def get_metrics(self) -> Dict[str, int]:
        """Returns coordinator execution metrics.

        Returns:
            Dict[str, int]: Plain dictionary containing job statistics.
        """
        with self._lock:
            self._active_futures = {f for f in self._active_futures if not f.done()}
            return {
                "submitted_jobs": self._submitted_jobs,
                "completed_jobs": self._completed_jobs,
                "failed_jobs": self._failed_jobs,
                "skipped_jobs": self._skipped_jobs,
                "pending_jobs": len(self._active_futures),
            }
