"""Main Window assembly for the Jarvis Desktop UI integration."""

import sys
import time
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QSplitter, QFrame, QMessageBox, QApplication, QDialog, QSystemTrayIcon
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QCloseEvent

from app.agent.models import AgentRequest
from app.voice.models import VoiceState
from app.core.exceptions import VoiceError
from app.utils.id_generator import generate_request_id
from app.config.settings import settings

from app.ui.theme import STYLE_MAIN, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_BLUE, ACCENT_GREEN, ACCENT_AMBER
from app.ui.threads import AgentWorker, VoiceWorker
from app.ui.tray import JarvisSystemTray
from app.ui.widgets.top_bar import TopBarWidget
from app.ui.widgets.chat_view import ChatViewWidget
from app.ui.widgets.sidebar import SidebarWidget
from app.ui.widgets.status_bar import StatusBarWidget
from app.ui.widgets.timeline import TimelineWidget
from app.ui.widgets.approval_card import ApprovalCardWidget
from app.ui.widgets.settings_dialog import SettingsDialog

logger = logging.getLogger("gui_app")


class MainWindow(QMainWindow):
    """Main window coordinating components, threads, and UI adapters."""

    def __init__(self, application: Any) -> None:
        super().__init__()
        self.application = application
        self.container = application.container
        self.controller = self.container.get("controller")
        
        # Threading state variables
        self.active_agent_worker: Optional[AgentWorker] = None
        self.active_voice_worker: Optional[VoiceWorker] = None
        self.pending_approval_card: Optional[ApprovalCardWidget] = None
        
        # Minimization behavior state
        self.close_to_tray_enabled = True
        self.force_exit_flag = False
        
        # Configure unhandled exceptions hooks
        sys.excepthook = self._unhandled_exception_hook
        
        self.setWindowTitle("Jarvis AI Assistant")
        self.resize(1000, 680)
        self.setStyleSheet(STYLE_MAIN)
        
        # System Tray Integration
        self.tray_icon = JarvisSystemTray(self)
        self.tray_icon.show()
        
        # Initialize UI Components
        self._init_layout()
        
        # Initial values load
        self._refresh_metrics()
        self._load_session_history()
        
        # Schedule periodic metrics refresh (e.g. every 5 seconds)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self._refresh_metrics)
        self.refresh_timer.start()

    def _init_layout(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left Splitter container: Chat (Top) + Timeline (Bottom)
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Top Bar
        self.top_bar = TopBarWidget()
        left_layout.addWidget(self.top_bar)
        
        # Splitter for Chat and Timeline
        splitter = QSplitter(Qt.Vertical)
        
        self.chat_view = ChatViewWidget()
        splitter.addWidget(self.chat_view)
        
        self.timeline = TimelineWidget()
        splitter.addWidget(self.timeline)
        
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        left_layout.addWidget(splitter)
        
        # Bottom Input Area
        input_container = QFrame()
        input_container.setStyleSheet(f"border-top: 1px solid #2f2f37; background-color: #121214;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)
        
        self.voice_btn = QPushButton("🎙️ Voice Mode")
        self.voice_btn.setCursor(Qt.PointingHandCursor)
        self.voice_btn.clicked.connect(self.toggle_voice_mode)
        input_layout.addWidget(self.voice_btn)
        
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type a message or command...")
        self.input_box.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_box)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        
        left_layout.addWidget(input_container)
        main_layout.addWidget(left_panel)
        
        # Right Sidebar Panel
        self.sidebar = SidebarWidget()
        main_layout.addWidget(self.sidebar)
        
        # Bottom Status Bar
        self.status_bar = StatusBarWidget()
        self.setStatusBar(self.status_bar)

    def _unhandled_exception_hook(self, exctype, value, traceback) -> None:
        """User-friendly notification mapping for unhandled exceptions."""
        logger.critical("Uncaught GUI Exception", exc_info=(exctype, value, traceback))
        QMessageBox.critical(
            self,
            "Critical Error",
            f"An unexpected critical error occurred:\n{value}\n\nThe system has logged this incident."
        )

    def _refresh_metrics(self) -> None:
        """Retrieves and populates current session metrics from core application components."""
        try:
            # 1. State indicator
            self.sidebar.update_state("Idle" if not self.active_agent_worker else "Thinking...")
            
            # 2. Database statistics
            mem_repo = self.container.get("memory_repository")
            conv_repo = self.container.get("conversation_repository")
            approval_mgr = self.container.get("approval_manager")
            
            mem_count = mem_repo.count()
            conv_count = len(conv_repo.list_sessions())
            self.sidebar.update_counts(mem_count, conv_count)
            
            # 3. Model/Provider info
            llm_manager = self.container.get("llm_manager")
            self.sidebar.update_model(settings.ollama_model)
            self.top_bar.set_model(settings.ollama_model)
            
            self.status_bar.update_provider_info(llm_manager.active_provider_name or "ollama", settings.ollama_model)
            self.status_bar.update_application_state(self.application.state.name)
            
            # 4. Scheduler Queue depth
            scheduler = self.container.get("inference_scheduler")
            self.status_bar.update_queue_depth(scheduler.get_queue_depth() if scheduler else 0)
            
            # 5. Pending approvals list in sidebar
            pending_actions = approval_mgr._repository.list_pending()
            self.sidebar.set_pending_approvals(pending_actions)
            
        except Exception as e:
            logger.error(f"Error refreshing sidebar metrics: {e}")

    def _load_session_history(self) -> None:
        """Retrieves existing active session messages and appends them to chat log."""
        self.chat_view.clear()
        
        active_session = self.container.get("conversation_active_session")
        if active_session:
            self.sidebar.update_session_info(active_session.session_id)
            messages = self.controller.conversation.get_history()
            for msg in messages:
                if msg.role.value in ("user", "assistant", "system", "tool"):
                    self.chat_view.add_message(msg.role.value, msg.content)

    @Slot()
    def send_message(self) -> None:
        """Submits text input, spawning the background agent worker thread."""
        if self.active_agent_worker:
            QMessageBox.warning(self, "Busy", "Please wait for Jarvis to complete the current request.")
            return
            
        user_text = self.input_box.text().strip()
        if not user_text:
            return
            
        self.input_box.clear()
        self.chat_view.add_message("user", user_text)
        
        # Clear old approval card if any
        self._clear_approval_card()
        
        # Clear old timeline steps
        self.timeline.clear()
        
        # Construct request object
        request = AgentRequest(
            request_id=generate_request_id(),
            text=user_text,
            source="gui",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        # Start Worker QThread
        self.active_agent_worker = AgentWorker(self.controller, self.container, request)
        self.active_agent_worker.chunk_received.connect(self._on_chunk_received)
        self.active_agent_worker.response_completed.connect(self._on_response_completed)
        self.active_agent_worker.approval_requested.connect(self._on_approval_requested)
        self.active_agent_worker.timeline_event.connect(self._on_timeline_event)
        self.active_agent_worker.error_occurred.connect(self._on_error_occurred)
        
        self.top_bar.set_status("Thinking...", ACCENT_BLUE)
        self.sidebar.update_state("Thinking...")
        
        self.active_agent_worker.start()

    @Slot(str)
    def _on_chunk_received(self, chunk: str) -> None:
        # For stream rendering, we could append chunks, but we can also just wait for complete text
        # or append chunk by chunk. To match bubbles, we can update or create a bubble once.
        # But wait! PySide6 text output chunk handling is clean. Let's just log it.
        pass

    @Slot(object)
    def _on_response_completed(self, message: Any) -> None:
        """Runs when agent finishes processing."""
        self.chat_view.add_message("assistant", message.content)
        self.top_bar.set_status("Ready", ACCENT_GREEN)
        self.sidebar.update_state("Idle")
        
        # Extract latency if present in message metrics
        latency_ms = message.metadata.get("latency_ms")
        if latency_ms:
            self.status_bar.update_latency(latency_ms)
            
        self.active_agent_worker = None
        self._refresh_metrics()

    @Slot(str, str, str, dict)
    def _on_approval_requested(self, action_id: str, tool_name: str, reason: str, arguments: dict) -> None:
        """Injects the interactive approval card widget directly into the chat view flow."""
        self.top_bar.set_status("Waiting Approval", ACCENT_AMBER)
        self.sidebar.update_state("Waiting Approval")
        
        card = ApprovalCardWidget(action_id, tool_name, reason, arguments)
        card.approval_resolved.connect(self._resolve_approval)
        
        # Embed card inside chat view directly
        self.chat_view.scroll_layout.addWidget(card)
        self.chat_view.scroll_to_bottom()
        self.pending_approval_card = card

    @Slot(str, bool)
    def _resolve_approval(self, action_id: str, approved: bool) -> None:
        """Resolves the pending action status in DB and wakes up agent worker thread."""
        approval_mgr = self.container.get("approval_manager")
        
        try:
            if approved:
                approval_mgr.approve(action_id)
            else:
                approval_mgr.reject(action_id)
        except Exception as e:
            logger.error(f"Error updating database approval state: {e}")
            
        self._clear_approval_card()
        
        # Wake up background worker thread
        if self.active_agent_worker:
            self.active_agent_worker.submit_approval_result(approved)
            self.top_bar.set_status("Thinking...", ACCENT_BLUE)
            self.sidebar.update_state("Thinking...")

    def _clear_approval_card(self) -> None:
        if self.pending_approval_card:
            self.chat_view.scroll_layout.removeWidget(self.pending_approval_card)
            self.pending_approval_card.deleteLater()
            self.pending_approval_card = None

    @Slot(str, str, str)
    def _on_timeline_event(self, event_name: str, details: str, timestamp_str: str) -> None:
        self.timeline.add_event(event_name, details, timestamp_str)

    @Slot(str)
    def _on_error_occurred(self, err_msg: str) -> None:
        self.top_bar.set_status("Error", "#ef476f")
        self.sidebar.update_state("Error")
        self.chat_view.add_message("system", f"[Error] Request failed: {err_msg}")
        self.active_agent_worker = None
        self._refresh_metrics()

    @Slot()
    def toggle_voice_mode(self) -> None:
        """Toggles push-to-talk voice thread runner."""
        if self.active_voice_worker:
            # Stop voice worker
            self.active_voice_worker.stop()
            self.active_voice_worker.wait()
            self.active_voice_worker = None
            self.voice_btn.setText("🎙️ Voice Mode")
            self.voice_btn.setObjectName("voiceBtn")
            self.voice_btn.setStyleSheet("")
            self.top_bar.update_mic_indicator(False)
            self.top_bar.set_status("Ready", ACCENT_GREEN)
            logger.info("Voice Mode deactivated.")
        else:
            # Lazy initialize sound device capture and start thread
            try:
                voice_runtime = self.container.get("voice_runtime")
                if not voice_runtime:
                    raise VoiceError("Voice Subsystem is not configured.")
                    
                self.active_voice_worker = VoiceWorker(voice_runtime)
                self.active_voice_worker.state_changed.connect(self._on_voice_state_changed)
                self.active_voice_worker.error_occurred.connect(self._on_voice_error)
                
                self.active_voice_worker.start()
                self.voice_btn.setText("🎙️ Active")
                self.voice_btn.setObjectName("voiceBtnActive")
                self.voice_btn.setStyleSheet(f"background-color: #ef476f; color: white;")
                self.top_bar.update_mic_indicator(True, "Idle")
                logger.info("Voice Mode activated.")
            except Exception as e:
                QMessageBox.critical(self, "Voice Error", f"Failed to activate voice mode: {e}")

    @Slot(object)
    def _on_voice_state_changed(self, state: VoiceState) -> None:
        """Maps runtime voice transitions directly to mic indicators without logic duplication."""
        self.top_bar.update_mic_indicator(state != VoiceState.STOPPED and state != VoiceState.IDLE, state.name)
        self.top_bar.set_status(state.name, ACCENT_BLUE if state != VoiceState.ERROR else "#ef476f")
        
        # If voice transitions to WAITING_APPROVAL, refresh metrics
        if state == VoiceState.WAITING_APPROVAL:
            self._refresh_metrics()

    @Slot(str)
    def _on_voice_error(self, err_msg: str) -> None:
        self.top_bar.set_status("Voice Error", "#ef476f")
        QMessageBox.warning(self, "Voice Input Warning", f"Voice capturing warning: {err_msg}")

    def open_settings_dialog(self) -> None:
        """Displays the settings configuration dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            # Refresh model label settings immediately
            self._refresh_metrics()

    def close_and_exit(self) -> None:
        """Forces full application termination, bypassing system tray minimize logic."""
        self.force_exit_flag = True
        self.close()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Intercepts window close buttons to minimize to system tray instead."""
        if self.close_to_tray_enabled and not self.force_exit_flag:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Jarvis minimized",
                "Jarvis continues running in background. Restore from system tray icon.",
                QSystemTrayIcon.Information,
                2000
            )
            logger.info("Main window minimized to system tray.")
        else:
            # Terminate active background threads
            if self.active_agent_worker:
                self.active_agent_worker.terminate()
            if self.active_voice_worker:
                self.active_voice_worker.stop()
                self.active_voice_worker.wait()
            self.tray_icon.hide()
            event.accept()
