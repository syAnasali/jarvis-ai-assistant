# Vision Subsystem Architecture & Local Multimodal Runtime

This document details the software architecture, visual analysis pipeline, local VLM integration, screen capture, OCR extraction layer, desktop tools, and extension guidelines for the provider-neutral Vision Runtime in Jarvis.

---

## 1. Overview

The Vision Runtime in `app/vision/` allows Jarvis to understand screenshots, active application windows, selected desktop regions, system clipboard images, on-screen error dialogs, terminal stack traces, and document charts. It operates fully offline using local multimodal models (e.g. `llava`, `qwen-vl` via Ollama) and local OCR (`pytesseract` / WinRT layout parsing).

---

## 2. Architecture & Data Flow

```
   Desktop Screen / Clipboard / File Input
                     │
                     ▼
         [ ScreenCapturer / Clipboard ]
                     │
                     ▼
             [ VisionImage ] (Structured Bytes & Metadata)
                     │
                     ▼
             [ Preprocessing & Crop ]
                     │
                     ▼
             [ LocalOCREngine ] ──► (Text, Code, Error Traces)
                     │
                     ▼
             [ VisionProvider ] (OllamaVisionProvider / VLM)
                     │
                     ▼
             [ VisionResponse ] ──► [ AgentController / Router ]
                                         │
                   ┌─────────────────────┼─────────────────────┐
                   ▼                     ▼                     ▼
          [ TaskPlanner Step ]   [ Memory System ]   [ Voice TTS Streaming ]
```

---

## 3. Key Pipeline Components

### 1. `VisionImage` & Immutable Models (`app/vision/models.py`)
- `VisionImage`: Structured container holding raw PCM image bytes, `ImageMetadata` (dimensions, aspect ratio, color mode, file size), intake source (`fullscreen`, `active_window`, `region`, `clipboard`, `file`), and timezone-aware timestamp.
- `VisionRequest`: Container encapsulating image asset, query prompt, optional bounding box focus region, and OCR configuration.
- `VisionResponse`: Response payload holding visual analysis description text, `OCRResult`, `DetectedRegion` bounding boxes, confidence score, and timing metadata.

### 2. `VisionProvider` (`OllamaVisionProvider` & `MockVisionProvider`)
- `OllamaVisionProvider`: Interfaces with local VLM instances via base64 encoded image chat payloads.
- Automatic fallback to `MockVisionProvider` when local VLM model is unavailable, ensuring robust zero-crash execution.

### 3. Screen Capture & Clipboard (`app/vision/capture.py` & `app/vision/clipboard.py`)
- `PILScreenCapturer`: Captures full screen (`capture_fullscreen`), active foreground window bounds (`capture_active_window`), or explicit bounding box region (`capture_region`).
- `PILClipboardImageRetriever`: Retrieves images directly from system clipboard (`get_clipboard_image`).

### 4. Local OCR Engine (`app/vision/ocr.py`)
- `LocalOCREngine`: Extracts printed text, code snippets, terminal outputs, error messages, and dialog text.
- Enriches VLM prompt context automatically when `enable_ocr=True`.

### 5. Vision Pipeline (`app/vision/pipeline.py`) & Subsystem Manager (`app/vision/manager.py`)
- Coordinates image intake -> preprocessing -> OCR -> VLM analysis -> `VisionResponse`.
- Features both synchronous `analyze()` and token streaming `stream_analyze()`.

---

## 4. Built-in System Tools (`app/tools/builtin/vision.py`)

| Tool Name | Permission | Description |
| :--- | :--- | :--- |
| `capture_screen` | `SAFE` | Captures full screen or active window and describes visual content. |
| `explain_error` | `SAFE` | Captures screen, performs OCR error trace extraction, and explains errors. |
| `read_clipboard_image` | `SAFE` | Retrieves clipboard image, extracts text via OCR, and provides visual description. |
| `analyze_region` | `SAFE` | Captures specified bounding box region `(x, y, w, h)` and analyzes content. |

---

## 5. Subsystem Integrations

### 1. TaskPlanner Integration
- The planner incorporates vision tools (e.g. `capture_screen`) as observation/reasoning steps before executing action tools (e.g., clicking or filling forms).

### 2. Memory System Integration & Safety Safeguards
- Vision-derived facts must satisfy `MemoryEvidenceValidator` constraints before being stored in long-term SQLite memory.
- Arbitrary OCR text is **never** persisted to long-term memory automatically.

### 3. Voice Subsystem Integration
- Spoken commands like *"What is on my screen?"* or *"Read this error"* invoke the Vision Runtime and stream the resulting analysis aloud via `PiperProvider` TTS.

---

## 6. Configuration Parameters (`app/config/settings.py`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VISION_ENABLED` | `True` | Master toggle for vision subsystem capabilities. |
| `VISION_PROVIDER` | `"ollama"` | Local VLM backend provider (`"ollama"` or `"mock"`). |
| `VISION_MODEL` | `"llava"` | Multimodal VLM model name (`"llava"`, `"qwen-vl"`). |
| `OCR_PROVIDER` | `"local"` | OCR engine provider backend (`"local"`). |
| `SCREENSHOT_FORMAT` | `"png"` | Target screenshot compression format (`"png"`/`"jpeg"`). |
| `OCR_LANGUAGE` | `"eng"` | OCR language dictionary code. |
| `MAX_IMAGE_SIZE` | `4096` | Maximum image dimension boundary. |

---

## 7. Diagnostic Verification Commands

Run standalone vision diagnostics:

```bash
.venv\Scripts\python scripts/test_vision_provider.py
.venv\Scripts\python scripts/test_screen_capture.py
.venv\Scripts\python scripts/test_clipboard_image.py
.venv\Scripts\python scripts/test_ocr.py
.venv\Scripts\python scripts/test_vision_pipeline.py
```
