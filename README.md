# Jarvis AI Assistant

[![Production Status](https://img.shields.io/badge/Status-100%25%20Production%20Ready-brightgreen)](file:///c:/Code-Playground/jarvis-ai-assistant/scripts/run_production_validation.py)
[![Python Version](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Jarvis AI Assistant is a production-oriented, offline-first, local AI assistant built with Python 3.13, Ollama, PySide6, and a modular agent architecture. It runs Large Language Models (LLMs) locally on your hardware to deliver maximum privacy, zero data leakage, and high-performance system control.

---

## Key Features

- **Local LLM Inference**: Offline model execution via Ollama API (`qwen2.5:7b` / `qwen3:8b`) with zero cloud dependencies.
- **Real-Time Token Streaming**: Word-by-word streaming generation with live chunk accumulator parsing.
- **Persistent Conversation Engine**: SQLite WAL database storage with session isolation, automatic context window trimming, and cross-restart message history persistence.
- **Multi-Type Persistent Memory**: Fact, preference, project context, and workspace memory classification with hybrid lexical/semantic retrieval, evidence validation, and background extraction.
- **Task Planning Runtime**: Sequential multi-step `TaskPlan` execution with reasoning steps, intermediate observation collection, and synthesis loops.
- **23 Built-in System Tools**:
  - **Filesystem Tools**: `inspect_path`, `list_directory`, `create_directory`, `create_file`, `write_text_file`, `move_path`, `delete_path`.
  - **Desktop Automation Tools**: `get_active_window`, `list_visible_windows`, `focus_window`, `type_text`, `press_key`, `press_hotkey`, `click_screen`.
  - **Application Launcher Tools**: `list_installed_applications`, `find_installed_application`, `resolve_application`, `launch_application`.
  - **System & Process Tools**: `get_current_time`, `get_system_info`, `get_disk_usage`, `list_running_processes`, `find_running_process`.
- **Synchronized Action Approval Runtime**: Modal confirmation dialog for `ToolPermission.CONFIRMATION` actions with indefinite OS console thread wait, zero expiration timeout during input, single input loop locking, and standardized lifecycle logging.
- **Offline Voice Interaction Pipeline**: Push-to-talk stateful loop using `faster-whisper` speech-to-text (STT), energy VAD, `pyttsx3` text-to-speech (TTS), and air-gapped voice tool approval safety suspension.
- **Professional Desktop GUI & System Tray**: Modern dark mode interface built with PySide6, featuring a system tray launcher, chat widget, active session monitor, and hotkey activation (`ctrl+alt+j`).
- **Priority Inference Scheduler**: Queue-based inference scheduler prioritizing interactive foreground requests over background memory extraction tasks.
- **Prompt & Context Optimization**: Regex-based dynamic tool schema filtering and system prompt trimming achieving 78.9% prompt size reduction.
- **Production Validation Suite**: Master developer validation script (`scripts/run_production_validation.py`) covering 405 unit tests, 9 end-to-end integration scenarios, 7 stress tests, and 8 performance latency benchmarks.

---

## Architecture Overview

Jarvis utilizes a decoupled, multi-layered architecture separating user interfaces, agent orchestration, safety approval runtimes, tool execution, and local model backends.

```
                  ┌──────────────────────────────────────────────────┐
                  │                 USER INTERFACES                  │
                  │   Terminal CLI  │  Voice (Whisper/TTS) │  GUI   │
                  └─────────────────────────┬────────────────────────┘
                                            │
                                            ▼
                                   [ AgentController ]
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
           [ Heuristic Router ]     [ TaskPlanner ]       [ MemoryManager ]
                    │                       │                       │
                    ▼                       ▼                       ▼
          [ Direct Execution ]    [ TaskPlan Executor ]   [ Hybrid Retriever ]
                    │                       │                       │
                    └───────────────────────┼───────────────────────┘
                                            │
                                            ▼
                                     [ AgentRunner ]
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
          [ LLMManager / Ollama ]                         [ ToolExecutor ]
                    │                                               │
                    ▼                                               ▼
           (Model Generation)                            {"permission": "CONFIRMATION"}
                                                                    │
                                                                    ▼
                                                         [ ApprovalManager / CLI ]
                                                         (Indefinite Blocking Wait)
```

For complete architectural diagrams and component specifications, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Technology Stack

- **Language**: Python 3.13
- **Local Inference Engine**: Ollama (`qwen2.5:7b` / `qwen3:8b`)
- **Desktop GUI**: PySide6 (Qt for Python)
- **Voice Pipeline**: `faster-whisper` (STT), `pyttsx3` (TTS)
- **Database Engine**: SQLite (WAL Mode)
- **Validation & Configuration**: Pydantic / Pydantic Settings
- **Structured Logging**: Loguru wrapped in `JarvisLogger`
- **Testing Framework**: Pytest

---

## Getting Started

### Prerequisites

1. Install and start [Ollama](https://ollama.com/).
2. Pull the default local model:
   ```bash
   ollama pull qwen2.5:7b
   ```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/syAnasali/jarvis-ai-assistant.git
   cd jarvis-ai-assistant
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment (Windows PowerShell):
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Copy the environment configuration:
   ```bash
   copy .env.example .env
   ```

---

## Usage Modes

### 1. Terminal Chat Mode (Default)
Interactive command-line chat session:
```bash
python main.py
```

### 2. Voice Mode
Push-to-talk voice interface with offline speech recognition and synthesis:
```bash
python main.py --voice
```

### 3. Professional Desktop GUI & System Tray
Launch the PySide6 desktop application with system tray integration:
```bash
python main.py --gui
```

---

## Testing & Validation

Run the complete Pytest unit and integration test suite:
```bash
.venv\Scripts\python -m pytest
```

Run the specialized blocking action approval workflow tests:
```bash
.venv\Scripts\python -m pytest tests/integration/test_blocking_approval_dialog.py
```

Execute the **Master Production Validation Suite** (validates all 13 subsystems, 9 integration scenarios, 7 stress tests, and 8 performance latency benchmarks):
```bash
.venv\Scripts\python scripts/run_production_validation.py
```

---

## Documentation Index

- [Architecture Reference](docs/ARCHITECTURE.md)
- [Project Structure Reference](docs/PROJECT_STRUCTURE.md)
- [Request Processing Flow](docs/REQUEST_FLOW.md)
- [Development Roadmap](docs/ROADMAP.md)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
