"""Asynchronous thread workers and signaling for PySide6 integration."""

import time
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from PySide6.QtCore import QThread, Signal
from app.agent.models import AgentRequest
from app.voice.models import VoiceState

logger = logging.getLogger("gui_threads")


class AgentWorker(QThread):
    """Background worker for executing AgentController chat requests without blocking GUI."""

    chunk_received = Signal(str)
    response_completed = Signal(object)  # Message object
    approval_requested = Signal(str, str, str, dict)  # action_id, tool_name, reason, arguments
    timeline_event = Signal(str, str, str)  # event_name, details, timestamp
    error_occurred = Signal(str)

    def __init__(self, controller: Any, container: Any, request: AgentRequest) -> None:
        super().__init__()
        self.controller = controller
        self.container = container
        self.request = request
        self.approval_event = threading.Event()
        self.approval_approved = False

    def submit_approval_result(self, approved: bool) -> None:
        """Called by GUI thread to resume agent execution with approval/rejection."""
        self.approval_approved = approved
        self.approval_event.set()

    def run(self) -> None:
        try:
            self.timeline_event.emit("USER_REQUEST", self.request.text, datetime.now(timezone.utc).isoformat())
            self.timeline_event.emit("PLANNER", "Classifying intent and routing request...", datetime.now(timezone.utc).isoformat())

            # Perform execution router check
            route = self.controller._router.route(self.request)
            self.timeline_event.emit("PLANNER", f"Routed to execution path: {route.mode.value}", datetime.now(timezone.utc).isoformat())

            active_approval_id = None
            
            while True:
                self.approval_event.clear()
                
                # Run the request streaming
                stream = self.controller.process_request_stream(self.request, approval_action_id=active_approval_id)
                for chunk in stream:
                    self.chunk_received.emit(chunk)

                # Check if suspended for confirmation
                messages = self.controller.conversation.get_history()
                if messages:
                    last_msg = messages[-1]
                    if last_msg.role.value == "assistant" and last_msg.metadata.get("confirmation_required"):
                        action_id = last_msg.metadata.get("pending_action_id")
                        tool_name = last_msg.metadata.get("tool_name")
                        reason = last_msg.metadata.get("reason", "")
                        
                        approval_manager = self.container.get("approval_manager")
                        action = approval_manager.get(action_id)
                        
                        if action:
                            self.timeline_event.emit(
                                "APPROVAL_REQUESTED", 
                                f"Suspended: Tool '{tool_name}' requires confirmation.", 
                                datetime.now(timezone.utc).isoformat()
                            )
                            self.approval_requested.emit(action_id, tool_name, reason, action.arguments)
                            
                            # Block thread waiting for GUI event to be set
                            self.approval_event.wait()
                            
                            if self.approval_approved:
                                self.timeline_event.emit("APPROVED", f"Action {action_id} approved.", datetime.now(timezone.utc).isoformat())
                                active_approval_id = action_id
                                continue
                            else:
                                self.timeline_event.emit("REJECTED", f"Action {action_id} rejected.", datetime.now(timezone.utc).isoformat())
                                active_approval_id = action_id
                                continue
                                
                # Request successfully completed (no suspension/resumption pending)
                if messages:
                    assistant_msg = messages[-1]
                    self.response_completed.emit(assistant_msg)
                    self.timeline_event.emit("COMPLETED", "Request execution finished.", datetime.now(timezone.utc).isoformat())
                break

        except Exception as e:
            logger.error(f"Error in AgentWorker: {e}")
            self.error_occurred.emit(str(e))
            self.timeline_event.emit("ERROR", f"Failed: {e}", datetime.now(timezone.utc).isoformat())


class VoiceWorker(QThread):
    """Background worker that runs the stateful VoiceRuntime loop."""

    state_changed = Signal(object)  # VoiceState
    error_occurred = Signal(str)

    def __init__(self, runtime: Any) -> None:
        super().__init__()
        self.runtime = runtime
        self.running = False
        
        # Connect runtime callback
        self.runtime.on_state_changed = self._on_state_changed

    def _on_state_changed(self, state: VoiceState) -> None:
        self.state_changed.emit(state)

    def stop(self) -> None:
        """Stops the voice capture loop."""
        self.running = False

    def run(self) -> None:
        self.running = True
        try:
            self.runtime.start()
            while self.running:
                try:
                    self.runtime.listen_and_process()
                except Exception as e:
                    logger.error(f"Voice runtime exception: {e}")
                    self.error_occurred.emit(str(e))
                    time.sleep(1)
        finally:
            self.runtime.stop()
