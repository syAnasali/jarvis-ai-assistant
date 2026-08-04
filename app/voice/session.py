"""Voice session tracker maintaining active session state and metrics."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.voice.models import VoiceState
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("voice_session")


@dataclass
class VoiceSession:
    """Session tracker for active voice interaction loop."""
    session_id: str = field(default_factory=lambda: f"vsession_{uuid.uuid4().hex[:8]}")
    state: VoiceState = VoiceState.IDLE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    utterance_count: int = 0
    interruption_count: int = 0
    total_audio_duration_seconds: float = 0.0

    def transition_to(self, new_state: VoiceState, reason: str = "") -> None:
        """Transitions session to a new state."""
        old_state = self.state
        if old_state == new_state:
            return

        self.state = new_state
        self.last_active_at = datetime.now(timezone.utc)
        if new_state == VoiceState.INTERRUPTED:
            self.interruption_count += 1
        elif new_state == VoiceState.STOPPED:
            self.ended_at = self.last_active_at

        log_msg = f"VoiceSession ({self.session_id}) state transition: {old_state.value} -> {new_state.value}"
        if reason:
            log_msg += f" (Reason: {reason})"
        logger.info(log_msg)

    def record_utterance(self, duration_seconds: float) -> None:
        """Records completed spoken utterance metrics."""
        self.utterance_count += 1
        self.total_audio_duration_seconds += max(0.0, duration_seconds)
        self.last_active_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Returns True if voice session is active."""
        return self.state not in (VoiceState.STOPPED, VoiceState.ERROR)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns session metrics summary."""
        now = datetime.now(timezone.utc)
        session_duration = (self.ended_at or now - self.created_at).total_seconds()
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "utterance_count": self.utterance_count,
            "interruption_count": self.interruption_count,
            "total_audio_duration_seconds": round(self.total_audio_duration_seconds, 2),
            "session_duration_seconds": round(session_duration, 2),
        }
