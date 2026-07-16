"""Unit tests for the local TTS plain-text normalization."""

from unittest.mock import MagicMock, patch
import pytest

from app.agent.models import AgentResponse
from app.voice.tts import PyTTSx3TTSProvider, normalize_text_for_speech


def test_text_normalization_for_speech() -> None:
    # Test headings and emphasis removal
    text1 = "# Main Heading\nThis is **bold** and *italic*."
    assert normalize_text_for_speech(text1) == "Main Heading This is bold and italic."

    # Test code blocks removal
    text2 = "Here is some code:\n```python\nprint('hello')\n```\nHope you like it."
    assert normalize_text_for_speech(text2) == "Here is some code: [code block] Hope you like it."

    # Test inline code backticks removal
    text3 = "Call the function `execute_action()`."
    assert normalize_text_for_speech(text3) == "Call the function execute_action()."

    # Test URLs simplification
    text4 = "Check out the website https://google.com for info."
    assert normalize_text_for_speech(text4) == "Check out the website link for info."

    # Test excessive whitespace normalization
    text5 = "Too   many \n\n  spaces."
    assert normalize_text_for_speech(text5) == "Too many spaces."


@patch("pyttsx3.init")
def test_tts_normalization_and_truncation(mock_pyttsx3_init) -> None:
    mock_engine = MagicMock()
    mock_pyttsx3_init.return_value = mock_engine

    # Configure provider with max_chars = 15
    provider = PyTTSx3TTSProvider(max_chars=15)
    provider.initialize()

    # Original AgentResponse
    original_text = "# Hello Jarvis\nThis text is very long!"
    response = AgentResponse(response_id="res_1", text=original_text)

    # Call speak
    res = provider.speak(response.text)

    # Ensure TTS engine was called with normalized, truncated version
    # Normalizes to: "Hello Jarvis This text is very long!"
    # Truncates at 15: "Hello Jarvis Th... [truncated]"
    mock_engine.say.assert_called_once_with("Hello Jarvis Th... [truncated]")
    assert res.success is True

    # Critical requirement: Original AgentResponse remains completely unchanged
    assert response.text == original_text
