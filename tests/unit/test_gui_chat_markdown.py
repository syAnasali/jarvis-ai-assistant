"""Unit tests for MarkdownRenderer."""

import pytest
from app.gui.chat.markdown import MarkdownRenderer


def test_markdown_renderer():
    text = "# Title\n**Bold**\n- Item"
    html = MarkdownRenderer.to_html(text)

    assert "<h1" in html
    assert "Title" in html
    assert "<b>Bold</b>" in html
    assert "• Item" in html
