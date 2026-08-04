"""Unit tests for EventTimelineRecorder."""

import pytest
from app.observability.timeline import EventTimelineRecorder
from app.observability.models import SubsystemName


def test_timeline_recording():
    timeline = EventTimelineRecorder()
    timeline.record_event("t_100", SubsystemName.VOICE, "Wake Word Detected", duration_ms=12.0)
    timeline.record_event("t_100", SubsystemName.VOICE, "STT Transcribed", duration_ms=120.0)

    events = timeline.get_timeline("t_100")
    assert len(events) == 2
    assert events[0].event_type == "Wake Word Detected"
    assert events[1].event_type == "STT Transcribed"
