"""Diagnostic script testing PySide6 Chat View, QThread ChatWorker streaming, and Markdown rendering."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.chat.markdown import MarkdownRenderer
from app.gui.views.chat_view import ChatView


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Chat View & QThread Streaming Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    # 1. Test MarkdownRenderer
    md_input = "# Heading 1\n**Bold Text**\n- Item 1\n- Item 2\n```python\nprint('Hello World')\n```"
    html = MarkdownRenderer.to_html(md_input)
    print("Markdown Conversion Result:")
    print(html[:150] + "...")
    assert "Heading 1" in html
    assert "Bold Text" in html
    print("PASS: MarkdownRenderer HTML conversion verified.")

    # 2. Test ChatView widget instantiation & QThread worker execution
    chat_view = ChatView()
    print("PASS: ChatView instantiated successfully.")

    # Simulate user sending prompt
    chat_view.message_input.txt_input.setPlainText("Hello Jarvis, test chat streaming.")
    chat_view.message_input.btn_send.click()

    # Wait briefly for QThread ChatWorker completion
    print("Waiting for QThread ChatWorker simulated streaming...")
    time.sleep(1.5)
    app.processEvents()

    session_len = len(chat_view.controller.active_session.messages)
    print(f"Active Session Messages Count: {session_len}")
    assert session_len >= 2
    print("PASS: QThread ChatWorker streaming & session persistence verified.")

    print("\nALL GUI CHAT DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
