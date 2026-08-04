"""ChatWorker QThread running backend LLM generation and tool execution off the UI thread."""

import time
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_chat_worker")


class ChatWorker(QThread):
    """QThread executing backend prompt generation and emitting PySide6 UI signals."""

    token_received = Signal(str)
    step_status = Signal(str)
    tool_executed = Signal(str, dict)
    generation_completed = Signal(str, list)
    generation_failed = Signal(str)

    def __init__(
        self,
        prompt: str,
        session_id: str = "default",
        agent_runner: Optional[Any] = None,
        parent: Optional[Any] = None
    ) -> None:
        super().__init__(parent)
        self.prompt = prompt
        self.session_id = session_id
        self.agent_runner = agent_runner
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flags active generation for cancellation."""
        self._is_cancelled = True

    def run(self) -> None:
        """Executes generation off-thread."""
        logger.info(f"ChatWorker started for prompt: '{self.prompt[:30]}...'")
        try:
            self.step_status.emit("Thinking...")

            if self.agent_runner and hasattr(self.agent_runner, "stream_run"):
                # Real backend execution
                full_text = ""
                citations: List[Dict[str, Any]] = []
                for chunk in self.agent_runner.stream_run(self.prompt):
                    if self._is_cancelled:
                        self.generation_failed.emit("Generation cancelled by user.")
                        return

                    if isinstance(chunk, str):
                        full_text += chunk
                        self.token_received.emit(chunk)
                    elif isinstance(chunk, dict) and chunk.get("type") == "tool":
                        self.step_status.emit(f"Calling Tool: {chunk.get('name')}")
                        self.tool_executed.emit(chunk.get("name", ""), chunk.get("result", {}))

                self.generation_completed.emit(full_text, citations)
            else:
                # Simulated streaming fallback for GUI testing
                sample_response = f"I have received your request: '{self.prompt}'. Processing with Jarvis backend engines..."
                tokens = sample_response.split(" ")
                full_text = ""
                for i, token in enumerate(tokens):
                    if self._is_cancelled:
                        self.generation_failed.emit("Generation cancelled by user.")
                        return
                    time.sleep(0.04)
                    t_str = token + (" " if i < len(tokens) - 1 else "")
                    full_text += t_str
                    self.token_received.emit(t_str)

                self.generation_completed.emit(full_text, [])

        except Exception as e:
            logger.error(f"ChatWorker generation failed: {e}")
            self.generation_failed.emit(str(e))
