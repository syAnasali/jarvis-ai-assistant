"""Diagnostic script testing PySide6 Voice & Vision Workspaces offscreen."""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, ".")

import time
from PySide6.QtWidgets import QApplication
from app.gui.views.vision_view import VisionView
from app.gui.views.voice_view import VoiceView


def main() -> None:
    print("==================================================")
    print("Testing PySide6 Voice & Vision Workspace Diagnostics")
    print("==================================================")

    app = QApplication.instance() or QApplication(sys.argv)

    # 1. VoiceView Diagnostics
    voice_view = VoiceView()
    print("PASS: VoiceView instantiated successfully.")

    voice_view.btn_talk.click()
    print("Waiting for QThread VoiceWorker simulated audio intake...")
    time.sleep(1.0)
    app.processEvents()

    assert voice_view.session_widget.lbl_user_transcript.text() != ""
    print("PASS: QThread VoiceWorker audio intake & transcript verified.")

    # 2. VisionView Diagnostics
    vision_view = VisionView()
    print("PASS: VisionView instantiated successfully.")

    vision_view.btn_full.click()
    print("Waiting for QThread VisionWorker simulated screen grab & OCR...")
    time.sleep(1.0)
    app.processEvents()

    assert vision_view.txt_ocr.toPlainText() != ""
    print("PASS: QThread VisionWorker screen grab & OCR extraction verified.")

    print("\nALL VOICE & VISION WORKSPACE DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
