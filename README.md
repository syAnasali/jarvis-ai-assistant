# Jarvis AI Assistant

Jarvis AI Assistant is a local desktop AI assistant built with Python, Ollama, and a modular agent architecture. It provides privacy-focused, offline-first interactions by running Large Language Models (LLMs) locally on your hardware.

> [!WARNING]
> This project is currently under active development. While the architecture is designed to be modular and production-oriented, the project is not yet production-ready.

---

## Current Status

Jarvis currently supports interactive, terminal-based conversations with a local Ollama model. The core orchestration, state handling, planning, execution, and LLM abstraction layers are fully established, allowing local chat execution.

---

## Key Features

- **Local LLM Execution**: Runs Large Language Models offline via the local Ollama API.
- **Qwen3 Integration**: Configured to run the local `qwen3:8b` model by default.
- **Provider Abstraction**: Decoupled LLM integration using the `BaseLLMProvider` interface to support alternative backend runtimes in the future.
- **Planning & Execution Pipeline**: Structured request routing using a dedicated `Planner` (to classify intents) and `Executor` (to process intents).
- **Session Conversation History**: In-memory session tracking and history compilation.
- **Configuration Management**: Type-safe settings loaded from environment variables and `.env` files using Pydantic Settings.
- **Structured Logging**: Standardized console and daily rotating file logs using Loguru, wrapped in a uniform `JarvisLogger` interface.
- **Provider Health Checks**: Consolidated connection verification and model availability checks.
- **Runtime Diagnostics**: Comprehensive system health status inspections (e.g. validating settings, logs, and data directories).
- **Centralized ID Generation**: Avoids duplicated ID logic using unified helpers.
- **Request Timing & Diagnostics**: Captures and logs request duration in milliseconds for performance analysis.

---

## Architecture Overview

The assistant uses a modular, layered structure to decouple user interfaces, session state, planning logic, and underlying models.

### Request/Response Data Flow

```
   [ User Input ]
         │
         ▼
    Terminal CLI
         │
         ▼
  AgentController ──(Adds User Message)──► Conversation (Session)
         │
         ▼
      Planner  ──(Creates Plan)──► ExecutionPlan
         │
         ▼
      Executor ──(Executes LLM path)
         │
         ▼
    LLMManager
         │
         ▼
   OllamaProvider
         │
         ▼
   [ Ollama Server ] ◄──► [ Local Qwen3 Model ]
         │
         ▼
   ResponseParser ──(Extracts Content)──► AgentResponse
         │
         ▼
  AgentController ──(Adds Assistant Message)──► Conversation (Session)
         │
         ▼
    Terminal Output
```

For more in-depth diagrams and details, see the [Architecture Documentation](file:///c:/Code-Playground/jarvis-ai-assistant/docs/ARCHITECTURE.md).

---

## Technology Stack

- **Language**: Python 3.13
- **Inference Runtime**: Ollama (Local Server)
- **Default LLM**: Qwen3 (8B Parameter Model)
- **Configuration & Validation**: Pydantic / Pydantic Settings
- **Logging Subsystem**: Loguru

---

## Getting Started

### Prerequisites

1. Install and start [Ollama](https://ollama.com/).
2. Pull the default local model:
   ```bash
   ollama pull qwen3:8b
   ```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jarvis-ai-assistant.git
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

5. Set up your environment configuration:
   ```bash
   copy .env.example .env
   ```

6. Open `.env` and verify the configured model:
   ```env
   OLLAMA_MODEL=qwen3:8b
   ```

### Running Jarvis

Execute the main entry point to start the terminal chat interface:
```bash
python main.py
```

---

## Configuration

Settings are managed via environment variables or loaded from the `.env` file at startup. The following variables are supported in `app/config/settings.py`:

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `APP_NAME` | The application name. | `"Jarvis AI Assistant"` |
| `APP_VERSION` | The version of the assistant. | `"0.1.0"` |
| `OLLAMA_HOST` | Ollama local server API host. | `"http://localhost:11434"` |
| `OLLAMA_MODEL` | The model name loaded in Ollama. | `"qwen3"` |
| `DATABASE_PATH` | Path to local database file. | `data/jarvis.db` |
| `LOG_LEVEL` | Application log output severity filter. | `"INFO"` |
| `VOICE_NAME` | Name of the configured voice synthesizer. | `"en-US-Neural"` |
| `HOTKEY` | Global key binding to activate the assistant window. | `"ctrl+alt+j"` |

---

## Running Jarvis (Example Session)

```
==================================================
Application: Jarvis AI Assistant
Version:     0.1.0
Provider:    ollama
Model:       qwen3:8b
Status:      Ready
==================================================
Type 'exit', 'quit', or 'bye' to end the session.

You > Hello! Introduce yourself in one sentence.
Jarvis > I am Jarvis, your local desktop AI assistant running entirely on your machine.

You > exit
Exiting chat session.
```

---

## Project Structure

A high-level overview of the repository structure is detailed below:

```
jarvis-ai-assistant/
├── app/                  # Application source package
│   ├── agent/            # Agent state, planning, and execution
│   ├── ai/               # Model provider interfaces and formatting
│   ├── config/           # Pydantic Settings and configurations
│   ├── core/             # Application orchestrator and bootstrappers
│   └── utils/            # Logging wrappers, ID generators, and banners
├── data/                 # Managed application directory (empty by default)
├── docs/                 # System architecture and workflow guides
├── logs/                 # Daily rotating runtime files (empty by default)
├── scripts/              # Isolated provider test scripts
├── tests/                # System test suite (empty by default)
└── main.py               # Main application entry point
```

For package and module-level responsibilities, reference the [Project Structure Documentation](file:///c:/Code-Playground/jarvis-ai-assistant/docs/PROJECT_STRUCTURE.md).

---

## Documentation Index

- [Architecture Reference](file:///c:/Code-Playground/jarvis-ai-assistant/docs/ARCHITECTURE.md)
- [Request Processing Flow](file:///c:/Code-Playground/jarvis-ai-assistant/docs/REQUEST_FLOW.md)
- [Project Structure Reference](file:///c:/Code-Playground/jarvis-ai-assistant/docs/PROJECT_STRUCTURE.md)
- [Development Roadmap](file:///c:/Code-Playground/jarvis-ai-assistant/docs/ROADMAP.md)

---

## Roadmap (Planned Features)

The following capabilities are planned for future development milestones:
- **Streaming Responses**: Support word-by-word streaming outputs in the chat interface.
- **Safe Tool Execution**: Sandbox and execute system operations (e.g. file reading/writing, web search).
- **Persistent Memory**: Integrate a SQLite database using SQLAlchemy to persist context across sessions.
- **Voice System**: Low-latency speech-to-text (Whisper/VAD) and text-to-speech (Kokoro) pipelines.
- **Desktop GUI**: Build a Qt-based PySide6 user interface and system tray integration.

---

## Contributing

Contributions will be opened once the core foundation matures. Contribution guides and formatting standards will be published in a future release.

---

## License

This project currently contains an empty `LICENSE` file. Please check back for updated licensing details as the project foundation matures.
