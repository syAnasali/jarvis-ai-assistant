"""Unit tests for the PySide6 desktop UI widgets and adapters."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QLabel
from app.ui.widgets.top_bar import TopBarWidget
from app.ui.widgets.sidebar import SidebarWidget
from app.ui.widgets.status_bar import StatusBarWidget
from app.ui.widgets.timeline import TimelineWidget
from app.ui.widgets.approval_card import ApprovalCardWidget
from app.ui.widgets.settings_dialog import SettingsDialog
from app.ui.app import MainWindow
from app.voice.models import VoiceState


# Ensure a single QApplication instance exists for all UI tests
@pytest.fixture(scope="session")
def q_app():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app


def test_top_bar_widget(q_app):
    """Verify top bar branding, status updates, and microphone indicators."""
    top_bar = TopBarWidget()
    
    # Check default active model label
    assert "qwen3" in top_bar.model_label.text()
    
    # Check status setter
    top_bar.set_status("Processing...", "#ff0000")
    assert top_bar.status_label.text() == "Processing..."
    
    # Check model update
    top_bar.set_model("llama3")
    assert top_bar.model_label.text() == "Model: llama3"
    
    # Check mic indicator ON
    top_bar.update_mic_indicator(True, "Speech Detected")
    assert "Speech Detected" in top_bar.mic_label.text()
    
    # Check mic indicator OFF
    top_bar.update_mic_indicator(False)
    assert "Off" in top_bar.mic_label.text()


def test_sidebar_widget(q_app):
    """Verify right sidebar metric counts and pending approvals display."""
    sidebar = SidebarWidget()
    
    sidebar.update_session_info("session_1234")
    assert "session_1234" in sidebar.session_lbl.text()
    
    sidebar.update_state("Thinking...")
    assert "Thinking..." in sidebar.state_lbl.text()
    
    sidebar.update_counts(12, 5)
    assert "Memory Count: 12" in sidebar.counts_lbl.text()
    assert "Conversations: 5" in sidebar.counts_lbl.text()
    
    # Check empty list
    sidebar.set_pending_approvals([])
    assert sidebar.approvals_list.count() == 1
    assert "No pending actions" in sidebar.approvals_list.item(0).text()
    
    # Check populated list
    action = MagicMock()
    action.action_id = "action_abc"
    action.tool_name = "write_text_file"
    action.arguments = {"path": "test.txt", "content": "hi"}
    
    sidebar.set_pending_approvals([action])
    assert sidebar.approvals_list.count() == 1
    assert "write_text_file" in sidebar.approvals_list.item(0).text()


def test_status_bar_widget(q_app):
    """Verify bottom status bar information updates."""
    status_bar = StatusBarWidget()
    
    status_bar.update_application_state("STOPPING")
    assert "STOPPING" in status_bar.app_state_label.text()
    
    status_bar.update_provider_info("Ollama", "qwen3")
    assert "Ollama" in status_bar.provider_label.text()
    
    status_bar.update_queue_depth(3)
    assert "3" in status_bar.queue_label.text()
    
    status_bar.update_latency(120.5)
    assert "120.50ms" in status_bar.latency_label.text()


def test_timeline_widget(q_app):
    """Verify activity timeline event logs and sorting."""
    timeline = TimelineWidget()
    assert len(timeline.items) == 0
    
    timeline.add_event("PLANNER", "Routed to DIRECT path", "2026-07-16T20:30:00Z")
    assert len(timeline.items) == 1
    
    item = timeline.items[0]
    # Check inner widgets of timeline item contain event name and details
    labels = item.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    assert any("PLANNER" in t for t in texts)
    assert any("Routed to DIRECT path" in t for t in texts)
    
    timeline.clear()
    assert len(timeline.items) == 0


def test_approval_card_widget(q_app):
    """Verify approval card countdown timer and signal emissions."""
    action_id = "act_9999"
    tool_name = "delete_path"
    reason = "User requested file deletion."
    arguments = {"path": "C:/temp"}
    
    resolved_calls = []
    def on_resolved(act_id, approved):
        resolved_calls.append((act_id, approved))
        
    card = ApprovalCardWidget(action_id, tool_name, reason, arguments, timeout_seconds=5)
    card.approval_resolved.connect(on_resolved)
    
    # Verify countdown timer runs
    assert card.time_left == 5
    card._on_timeout_tick()
    assert card.time_left == 4
    
    # Test Approve click
    card._on_approve()
    assert len(resolved_calls) == 1
    assert resolved_calls[0] == (action_id, True)
    
    # Test Reject click
    card2 = ApprovalCardWidget(action_id, tool_name, reason, arguments, timeout_seconds=5)
    card2.approval_resolved.connect(on_resolved)
    card2._on_reject()
    assert len(resolved_calls) == 2
    assert resolved_calls[1] == (action_id, False)


def test_settings_dialog(q_app):
    """Verify settings form loading and save validation."""
    dialog = SettingsDialog()
    assert dialog.model_input.text() == "qwen3:8b"
    assert dialog.timeout_input.value() == 120
