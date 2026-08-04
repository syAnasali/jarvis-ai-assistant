"""Unit tests for PlaybackManager queueing and thread safety."""

import pytest
from app.voice.playback import PlaybackManager


def test_playback_manager_enqueue_and_is_playing():
    playback = PlaybackManager()
    assert playback.is_playing() is False

    playback.enqueue_chunk(b"\x00\x00" * 100)
    assert playback.is_playing() is True

    health = playback.health_check()
    assert health["queue_size"] == 1
    assert health["interrupted"] is False


def test_playback_manager_interrupt():
    playback = PlaybackManager()
    playback.enqueue_chunk(b"\x00\x00" * 100)
    playback.enqueue_chunk(b"\x00\x00" * 200)

    playback.interrupt(reason="User barge-in")
    assert playback.is_playing() is False
    assert playback.health_check()["queue_size"] == 0
    assert playback.health_check()["interrupted"] is True


def test_playback_manager_stream_playback():
    playback = PlaybackManager()
    chunks = [b"\x00\x00" * 50, b"\x00\x00" * 50]
    playback.stream_playback(chunks)
    assert isinstance(playback.health_check()["queue_size"], int)
