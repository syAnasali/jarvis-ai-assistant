"""Settings Dialog for modifying application configuration."""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QCheckBox, QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt, Slot
from app.config.settings import settings


class SettingsDialog(QDialog):
    """Configuration dialog for editing model, voice, logging, and window behaviors."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(380, 420)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1e;
                color: #e3e3e6;
            }
            QLabel {
                color: #e3e3e6;
                font-weight: bold;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #232329;
                border: 1px solid #2f2f37;
                border-radius: 4px;
                color: #e3e3e6;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Model Configuration
        self.model_lbl = QLabel("Ollama Model:")
        layout.addWidget(self.model_lbl)
        self.model_input = QLineEdit(settings.ollama_model)
        layout.addWidget(self.model_input)
        
        # 2. Voice Config (Enabled and Voice Name)
        self.voice_enabled_chk = QCheckBox("Enable Voice Mode")
        self.voice_enabled_chk.setChecked(settings.voice_enabled)
        layout.addWidget(self.voice_enabled_chk)
        
        self.voice_lbl = QLabel("Voice (TTS Engine Name/ID):")
        layout.addWidget(self.voice_lbl)
        self.voice_input = QLineEdit(settings.voice_name)
        layout.addWidget(self.voice_input)
        
        # 3. Log Level Configuration
        self.log_lbl = QLabel("Log Level:")
        layout.addWidget(self.log_lbl)
        self.log_select = QComboBox()
        self.log_select.addItems(["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"])
        self.log_select.setCurrentText(settings.log_level)
        layout.addWidget(self.log_select)
        
        # 4. Approval Timeout
        self.timeout_lbl = QLabel("Approval Timeout (seconds):")
        layout.addWidget(self.timeout_lbl)
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(10, 3600)
        self.timeout_input.setValue(settings.approval_timeout_seconds or 120)
        layout.addWidget(self.timeout_input)
        
        # 5. Window Minimize Behavior
        self.tray_behavior_chk = QCheckBox("Minimize to Tray on Close")
        # Default behavior to True as per sprint specs
        self.tray_behavior_chk.setChecked(True)
        layout.addWidget(self.tray_behavior_chk)
        
        layout.addStretch()
        
        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #232329;
                border: 1px solid #2f2f37;
                color: #e3e3e6;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2f2f37;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a86ff;
                border: 1px solid #3a86ff;
                color: white;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)

    @Slot()
    def _save_settings(self) -> None:
        """Saves current widget values to singleton and persists in .env."""
        model = self.model_input.text().strip()
        voice_enabled = self.voice_enabled_chk.isChecked()
        voice = self.voice_input.text().strip()
        log_level = self.log_select.currentText()
        timeout = self.timeout_input.value()
        
        if not model:
            QMessageBox.critical(self, "Error", "Model name cannot be empty.")
            return

        # Update singleton settings
        settings.ollama_model = model
        settings.voice_enabled = voice_enabled
        settings.voice_name = voice
        settings.log_level = log_level
        settings.approval_timeout_seconds = timeout
        
        # Persist to .env file
        try:
            self._write_env_file(model, voice, log_level, voice_enabled, timeout)
            QMessageBox.information(self, "Settings Saved", "Settings successfully saved and persisted to .env.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Settings", f"Failed to persist settings: {e}")

    def _write_env_file(self, model: str, voice: str, log_level: str, voice_enabled: bool, timeout: int) -> None:
        env_path = Path(".env")
        lines = []
        keys_updated = set()
        
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.split("=", 1)
                    key_strip = key.strip()
                    if key_strip == "OLLAMA_MODEL":
                        lines.append(f"OLLAMA_MODEL={model}")
                        keys_updated.add("OLLAMA_MODEL")
                    elif key_strip == "VOICE_NAME":
                        lines.append(f"VOICE_NAME={voice}")
                        keys_updated.add("VOICE_NAME")
                    elif key_strip == "LOG_LEVEL":
                        lines.append(f"LOG_LEVEL={log_level}")
                        keys_updated.add("LOG_LEVEL")
                    elif key_strip == "VOICE_ENABLED":
                        lines.append(f"VOICE_ENABLED={str(voice_enabled)}")
                        keys_updated.add("VOICE_ENABLED")
                    elif key_strip == "APPROVAL_TIMEOUT_SECONDS":
                        lines.append(f"APPROVAL_TIMEOUT_SECONDS={timeout}")
                        keys_updated.add("APPROVAL_TIMEOUT_SECONDS")
                    else:
                        lines.append(line)
                else:
                    lines.append(line)
                    
            if "OLLAMA_MODEL" not in keys_updated:
                lines.append(f"OLLAMA_MODEL={model}")
            if "VOICE_NAME" not in keys_updated:
                lines.append(f"VOICE_NAME={voice}")
            if "LOG_LEVEL" not in keys_updated:
                lines.append(f"LOG_LEVEL={log_level}")
            if "VOICE_ENABLED" not in keys_updated:
                lines.append(f"VOICE_ENABLED={str(voice_enabled)}")
            if "APPROVAL_TIMEOUT_SECONDS" not in keys_updated:
                lines.append(f"APPROVAL_TIMEOUT_SECONDS={timeout}")
        else:
            lines = [
                f"OLLAMA_MODEL={model}",
                f"VOICE_NAME={voice}",
                f"LOG_LEVEL={log_level}",
                f"VOICE_ENABLED={str(voice_enabled)}",
                f"APPROVAL_TIMEOUT_SECONDS={timeout}"
            ]
            
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
