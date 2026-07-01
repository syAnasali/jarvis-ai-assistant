# Jarvis AI Assistant

Production-grade Desktop AI Assistant built using Python and local LLMs.

Status:
🚧 Under Development

---

## Project Description
Jarvis AI Assistant is a high-performance desktop assistant designed to execute tasks, process information, and interact with the user via text, voice, and system integrations. It operates primarily using local machine learning models for LLM inference, voice activity detection, speech-to-text, and text-to-speech, ensuring user data privacy and low latency.

## Goals
- **Local-First Execution**: Prioritize privacy and offline compatibility by running models locally.
- **Extensible Tool Registry**: Enable the assistant to interact with local files, APIs, and OS systems through safe, validated tools.
- **Multimodal Interaction**: Support seamless switching between text and low-latency voice dialogue.
- **Persistent Context**: Retain short-term conversation state and long-term memory across sessions using a robust database layer.

## Technology Stack
- **Language**: Python >= 3.13
- **Inference**: Ollama (LLM reasoning)
- **Speech-to-Text**: Faster Whisper
- **Voice Detection**: Silero VAD
- **Text-to-Speech**: Kokoro
- **GUI Framework**: PySide6 (Qt for Python)
- **Database Engine**: SQLAlchemy & SQLite
- **Environment & Configuration**: Pydantic / Pydantic Settings & Python-dotenv
- **Testing & Quality**: pytest & Ruff

## Folder Structure
For detailed explanations of the folders and packages, see [FOLDER_STRUCTURE.md](file:///c:/Code-Playground/jarvis-ai-assistant/docs/FOLDER_STRUCTURE.md).

```
jarvis-ai-assistant/
├── app/                  # Application packages (ai, core, config, memory, prompts, tools, ui, voice, etc.)
├── assets/               # Static media resources
├── data/                 # Local data and SQLite databases
├── docs/                 # System architecture and roadmap documentation
├── logs/                 # Application log files
├── scripts/              # Development and administration utility scripts
└── tests/                # System test suite
```

## Architecture Summary
The application is designed using a modular, layered architecture to achieve clear separation of concerns.

| Layer | Responsibility |
| :--- | :--- |
| **Presentation** | Desktop UI, voice input capture, voice synthesis, and desktop notifications. |
| **Application** | Execution of the agent loop, conversation flows, and orchestrating interactions. |
| **AI** | Constructing prompt templates, coordinating LLM communication, and tool parsing. |
| **Tool** | Registration, parameter validation, and secure execution of functions. |
| **Memory** | Managing short-term session history and long-term memory via SQLite. |
| **Infrastructure** | Logging, global configuration properties, and shared utilities. |

For a detailed view of the system components and flowcharts, reference [ARCHITECTURE.md](file:///c:/Code-Playground/jarvis-ai-assistant/docs/ARCHITECTURE.md).

## Development Roadmap
The project will be built out in structured phases:
1. **Phase 1**: Repository Foundation
2. **Phase 2**: Core Infrastructure
3. **Phase 3**: LLM Integration
4. **Phase 4**: Agent Loop
5. **Phase 5**: Tool Calling
6. **Phase 6**: Memory Engine
7. **Phase 7**: Voice System
8. **Phase 8**: Desktop Interface
9. **Phase 9**: Advanced Features
10. **Phase 10**: Testing
11. **Phase 11**: Packaging
12. **Phase 12**: Documentation

See [ROADMAP.md](file:///c:/Code-Playground/jarvis-ai-assistant/docs/ROADMAP.md) for detailed deliverables and milestones of each phase.

## Installation
*(Placeholder - Installation instructions will be provided once Phase 11 is complete)*

```bash
# Clone the repository
git clone https://github.com/yourusername/jarvis-ai-assistant.git

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## License
This project is licensed under the terms specified in the [LICENSE](file:///c:/Code-Playground/jarvis-ai-assistant/LICENSE) file.
