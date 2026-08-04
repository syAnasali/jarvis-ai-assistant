"""MarkdownRenderer converting raw Markdown to PySide6 Rich Text HTML."""

import re
from typing import Dict, List


class MarkdownRenderer:
    """Parses raw Markdown strings into PySide6 Rich Text HTML."""

    @classmethod
    def to_html(cls, text: str) -> str:
        """Converts Markdown text to formatted HTML string."""
        if not text:
            return ""

        # Escape raw HTML special characters
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Code blocks placeholders
        code_blocks: List[str] = []

        def _code_block_sub(match: re.Match) -> str:
            lang = match.group(1) or ""
            code_content = match.group(2)
            idx = len(code_blocks)
            code_blocks.append(f'<div class="code-block" data-lang="{lang}"><pre><code>{code_content}</code></pre></div>')
            return f"<!--CODEBLOCK_{idx}-->"

        html = re.sub(r"```(\w*)\n(.*?)```", _code_block_sub, html, flags=re.DOTALL)

        # Inline code
        html = re.sub(r"`([^`]+)`", r'<code style="background-color: #242838; padding: 2px 5px; border-radius: 4px; font-family: monospace;">\1</code>', html)

        # Headings
        html = re.sub(r"^### (.*?)$", r'<h3 style="font-size: 15px; margin-top: 8px; font-weight: 600; color: #818cf8;">\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r"^## (.*?)$", r'<h2 style="font-size: 17px; margin-top: 10px; font-weight: 600; color: #818cf8;">\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r"^# (.*?)$", r'<h1 style="font-size: 19px; margin-top: 12px; font-weight: 600; color: #818cf8;">\1</h1>', html, flags=re.MULTILINE)

        # Bold & Italic
        html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html)
        html = re.sub(r"\*(.*?)\*", r"<i>\1</i>", html)

        # Blockquotes
        html = re.sub(r"^&gt; (.*?)$", r'<blockquote style="border-left: 3px solid #6366f1; padding-left: 8px; color: #94a3b8;">\1</blockquote>', html, flags=re.MULTILINE)

        # Links
        html = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" style="color: #818cf8; text-decoration: underline;">\1</a>', html)

        # Bullet lists
        html = re.sub(r"^\* (.*?)$", r"• \1<br/>", html, flags=re.MULTILINE)
        html = re.sub(r"^- (.*?)$", r"• \1<br/>", html, flags=re.MULTILINE)

        # Restore Code blocks
        for i, cb in enumerate(code_blocks):
            html = html.replace(f"<!--CODEBLOCK_{i}-->", cb)

        # Replace newlines with breaks for simple paragraphs
        html = html.replace("\n", "<br/>")
        return html
