# Voice Subsystem Architecture & Full-Duplex Runtime

This document details the software architecture, execution flow, provider interfaces, configuration parameters, and extension boundaries of the full-duplex local voice assistant runtime for Jarvis.

---

## 1. Overview

The voice subsystem in `app/voice/` provides an offline-first, full-duplex speech interaction pipeline. It runs speech recognition (`faster-whisper`), voice activity detection, wake word detection ("Hey Jarvis"), sentence-level streaming speech synthesis (`PiperProvider` / `PyTTSx3TTSProvider`), barge-in audio interruption, and voice-based action approval handling without modifying the core agent text chat runtime.

---

## 2. Architecture & Pipeline Lifecycle

```
Microphone Audio Input
        │
        ▼
   [ AudioCapture ] (PCM 16kHz)
        │
        ▼
   [ VoiceActivityDetector ] ──► [ WakeWordDetector ] ("Hey Jarvis")
        │
        ▼
   [ SpeechToTextProvider ] (FasterWhisperProvider: tiny, base, small, medium)
        │
        ▼
   [ AgentController / Router ] ──► [ Conversation & Memory Engine ]
        │
        ▼
   [ Streaming LLM Token Stream ]
        │
        ▼
   [ Sentence Chunker ] (Splits token stream on [.!?\n])
        │
        ▼
   [ TextToSpeechProvider ] (PiperProvider / PyTTSx3TTSProvider)
        │
        ▼
   [ PlaybackManager ] ──► Speaker Audio Output
        │
        ▲ (User Spoken Input / Barge-In Interrupt)
        │
   (Interrupts Playback & Clears Queue)
```

---

## 3. Key Pipeline Components

### 1. `SpeechToTextProvider` (`FasterWhisperProvider`)
- Local offline transcription powered by `faster-whisper`.
- Supports configurable model sizes (`tiny`, `base`, `small`, `medium`).
- Automatic compute device selection (GPU CUDA execution with seamless CPU fallback).
- Supports batch audio segment transcription and streaming frame transcription.

### 2. `TextToSpeechProvider` (`PiperProvider` / `PyTTSx3TTSProvider`)
- `PiperProvider`: Local neural speech synthesis with configurable voice model, speaking speed, volume, and sample rate.
- `PyTTSx3TTSProvider`: Offline Windows SAPI5 synthesizer fallback.
- Plain text normalizer strips raw Markdown syntax, code blocks, and headings prior to synthesis.

### 3. `VoiceActivityDetector` (`EnergyBasedVAD`)
- RMS energy-based voice activity detector with noise floor calibration.
- Detects speech start and trailing silence end boundaries dynamically without fixed recording length limits.

### 4. `WakeWordDetector` (`LocalWakeWordDetector`)
- Detects trigger phrase ("Hey Jarvis").
- Operational modes:
  - `ALWAYS_LISTENING`: Continuously inspects audio frames for wake word.
  - `PUSH_TO_TALK`: Triggered via hotkey or spacebar.
  - `DISABLED`: Direct speech processing without wake phrase requirement.

### 5. `VoiceSession` (`app/voice/session.py`)
- Tracks session lifecycle states (`IDLE`, `LISTENING`, `TRANSCRIBING`, `PROCESSING`, `WAITING_APPROVAL`, `SPEAKING`, `INTERRUPTED`, `STOPPED`).
- Records metrics including session duration, utterance count, total audio seconds, and barge-in interruption count.

### 6. `PlaybackManager` (`app/voice/playback.py`)
- Thread-safe audio output stream manager.
- Supports instant `stop()` and `interrupt()` calls when user speech is detected during assistant playback.

### 7. Sentence-Level Streaming TTS Pipeline
- Reuses the `AgentController.process_request_stream()` token generator.
- `chunk_sentences` parses token fragments into sentence units (`.`, `!`, `?`, `\n`) and immediately feeds them into `TextToSpeechProvider` -> `PlaybackManager`.
- Synthesized speech begins playing aloud before the LLM finishes generating the full response text.

### 8. Voice-Based Approval Workflow
- When a voice command triggers a tool with `ToolPermission.CONFIRMATION` (e.g. `delete_path`), Jarvis speaks:
  *"I need your approval to execute delete_path. Please say 'yes' to confirm or 'no' to cancel."*
- Session transitions to `WAITING_APPROVAL`.
- Spoken responses:
  - `"yes"` / `"approve"` / `"confirm"` -> calls `ApprovalManager.approve(action_id)` and resumes execution.
  - `"no"` / `"cancel"` / `"reject"` -> calls `ApprovalManager.reject(action_id)` and cancels execution cleanly.

---

## 4. Configuration Parameters

The voice subsystem settings are declared in `app/config/settings.py`:

| Setting Variable | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `VOICE_ENABLED` | `bool` | `True` | Master toggle for voice subsystem capabilities. |
| `VOICE_STT_PROVIDER` | `str` | `"faster_whisper"` | Speech-to-text provider backend (`"faster_whisper"`). |
| `VOICE_TTS_PROVIDER` | `str` | `"piper"` | Text-to-speech provider backend (`"piper"` or `"pyttsx3"`). |
| `VOICE_LANGUAGE` | `str` | `"en"` | Language code for STT and TTS engines. |
| `VOICE_SAMPLE_RATE` | `int` | `16000` | Audio sampling rate in Hertz (16kHz standard). |
| `VOICE_WAKE_WORD` | `str` | `"Hey Jarvis"` | Wake phrase string for activation. |
| `VOICE_VAD_THRESHOLD` | `float` | `0.02` | RMS energy threshold multiplier for VAD. |
| `VOICE_PUSH_TO_TALK` | `bool` | `True` | Toggles push-to-talk key activation vs continuous listening. |

---

## 5. Diagnostic Commands & Verification

Run standalone diagnostic scripts to verify each component:

```bash
.venv\Scripts\python scripts/test_voice_pipeline.py
.venv\Scripts\python scripts/test_stt.py
.venv\Scripts\python scripts/test_tts.py
.venv\Scripts\python scripts/test_voice_session.py
.venv\Scripts\python scripts/test_wakeword.py
.venv\Scripts\python scripts/test_vad.py
```
