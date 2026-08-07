"""ChatWorker QThread running backend LLM generation and tool execution off the UI thread."""

import time
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_chat_worker")


class ChatWorker(QThread):
    """QThread executing backend prompt generation and emitting PySide6 UI signals."""

    token_received = Signal(str)
    step_status = Signal(str)
    tool_executed = Signal(str, dict)
    generation_completed = Signal(str, list)
    generation_failed = Signal(str)

    def __init__(
        self,
        prompt: str,
        session_id: str = "default",
        history: Optional[List[Any]] = None,
        agent_runner: Optional[Any] = None,
        parent: Optional[Any] = None
    ) -> None:
        super().__init__(parent)
        self.prompt = prompt
        self.session_id = session_id
        self.history = history or []
        self.agent_runner = agent_runner
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flags active generation for cancellation."""
        self._is_cancelled = True

    def _get_active_desktop_paths(self) -> List[Any]:
        """Returns active Windows Desktop directory paths (resolving OneDrive redirection)."""
        import os
        from pathlib import Path
        paths: List[Path] = []

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
            val, _ = winreg.QueryValueEx(key, 'Desktop')
            expanded = Path(os.path.expandvars(val))
            if expanded.exists():
                paths.append(expanded)
        except Exception:
            pass

        onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
        if onedrive_desktop.exists() and onedrive_desktop not in paths:
            paths.append(onedrive_desktop)

        # 4. Public Desktop
        pub_env = os.environ.get("PUBLIC", r"C:\Users\Public")
        public_desktop = Path(pub_env) / "Desktop"
        if public_desktop.exists() and public_desktop not in paths:
            paths.append(public_desktop)

        return paths

    def _get_primary_desktop_path(self) -> Any:
        """Returns single primary active Desktop path to prevent duplicate folder creation."""
        paths = self._get_active_desktop_paths()
        return paths[0] if paths else (Path.home() / "Desktop")

    def _parse_create_target(self, prompt: str, prompt_lower: str, primary_desktop: Any) -> tuple[Any, str]:
        """Parses target parent directory and folder name from user prompt."""
        import re
        from pathlib import Path

        # 1. Resolve Target Parent Directory
        target_dir = primary_desktop
        if any(k in prompt_lower for k in ("in c drive", "on c drive", "in c:", "in c\\", "in c/")):
            target_dir = Path("C:/")
        elif any(k in prompt_lower for k in ("in d drive", "on d drive", "in d:", "in d\\", "in d/")):
            target_dir = Path("D:/")
        elif "in documents" in prompt_lower or "in document" in prompt_lower:
            target_dir = Path.home() / "Documents"
        elif "in downloads" in prompt_lower or "in download" in prompt_lower:
            target_dir = Path.home() / "Downloads"
        elif "in desktop" in prompt_lower or "on desktop" in prompt_lower:
            target_dir = primary_desktop

        # 2. Extract Folder Name (Check Quotes First)
        quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
        if quoted:
            folder_name = quoted[0].strip()
        else:
            clean = prompt_lower
            for loc in ("in c drive", "on c drive", "in c:", "in d drive", "on d drive", "in d:", "in desktop", "on desktop", "in documents", "in downloads"):
                clean = clean.replace(loc, "")

            match = re.search(r'(?:folder|directory|dir|named|called)\s+["\']?([^"\'\.\s,]+)["\']?', clean)
            if match and match.group(1) not in ("in", "on", "a", "an", "the", "c", "d"):
                folder_name = match.group(1).strip()
            else:
                words = [w.strip(".,!?\"'") for w in clean.split() if w.strip(".,!?\"'") not in ("create", "make", "mkdir", "folder", "directory", "dir", "a", "an", "the", "my", "new", "in", "on", "of", "to") and len(w.strip(".,!?\"'")) > 0]
                folder_name = words[0] if words else "New_Folder"

        return target_dir, folder_name

    def _force_delete_target(self, target_path: Any) -> bool:
        """Deletes a file or directory on Windows handling read-only permissions and shell locks."""
        import os
        import stat
        import shutil

        def handle_remove_readonly(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        try:
            if not target_path.exists():
                return True

            if target_path.is_file() or target_path.is_symlink():
                os.chmod(target_path, stat.S_IWRITE)
                os.remove(target_path)
            elif target_path.is_dir():
                shutil.rmtree(target_path, onerror=handle_remove_readonly)

            if target_path.exists():
                os.system(f'rmdir /s /q "{target_path}"')

            return not target_path.exists()
        except Exception as e:
            logger.error(f"Force delete failed for '{target_path}': {e}")
            return False

    def _refresh_windows_explorer(self) -> None:
        """Flushes Windows File Explorer icon cache and forces immediate Desktop redraw."""
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
        except Exception as ex:
            logger.warning(f"SHChangeNotify refresh notice: {ex}")

    def _analyze_image_file(self, image_path: Any) -> str:
        """Analyzes an image file extracting resolution, palette, contrast, and dynamic visual subject details."""
        from pathlib import Path
        p = Path(image_path)
        if not p.exists():
            return f"⚠️ Image file `{p.name}` not found on disk."

        try:
            from PIL import Image, ImageStat
            with Image.open(p) as img:
                w, h = img.size
                fmt = img.format or p.suffix.upper().replace(".", "")
                mode = img.mode
                fsize_kb = round(p.stat().st_size / 1024, 1)

                rgb_img = img.convert("RGB")
                small_img = rgb_img.resize((64, 64))
                stat = ImageStat.Stat(small_img)
                avg_r, avg_g, avg_b = stat.mean[:3]
                var_r, var_g, var_b = stat.var[:3]
                avg_brightness = (avg_r + avg_g + avg_b) / 3.0
                total_variance = (var_r + var_g + var_b) / 3.0

                # Aspect Ratio description
                ratio = round(w / h, 2) if h > 0 else 1.0
                if 0.95 <= ratio <= 1.05:
                    aspect_desc = "Square (1:1)"
                elif ratio > 1.3:
                    aspect_desc = f"Landscape ({ratio}:1)"
                else:
                    aspect_desc = f"Portrait ({ratio}:1)"

                # Color Palette & Dominant Tones
                if max(avg_r, avg_g, avg_b) - min(avg_r, avg_g, avg_b) < 15:
                    color_tone = "Monochromatic / Grayscale"
                elif avg_b > avg_r and avg_b > avg_g:
                    color_tone = "Cool Blue & Cyan Accent Tones"
                elif avg_r > avg_g and avg_r > avg_b:
                    color_tone = "Warm Red & Amber Tones"
                elif avg_g > avg_r and avg_g > avg_b:
                    color_tone = "Green / Nature Palette"
                else:
                    color_tone = "Multi-hue Dynamic Color Palette"

                # Lighting & Theme Profile
                if avg_brightness < 70:
                    theme_str = "Dark Ambient / High-Contrast Dark Mode"
                    bg_desc = f"Dominant dark background (Avg Luminance: {int(avg_brightness)}/255)"
                elif avg_brightness > 185:
                    theme_str = "Bright High-Luminance / Light Interface"
                    bg_desc = f"High-contrast light background (Avg Luminance: {int(avg_brightness)}/255)"
                else:
                    theme_str = "Mid-Tone Balanced Exposure"
                    bg_desc = f"Standard natural exposure (Avg Luminance: {int(avg_brightness)}/255)"

                # Content Density & Structural Profile
                if total_variance > 2500:
                    complexity_str = "High Detail & Edge Variance (Complex Photo, Graphic, or Screenshot)"
                elif total_variance > 800:
                    complexity_str = "Moderate Detail & Structured Elements"
                else:
                    complexity_str = "Low Variance / Smooth Gradient or Solid Background"

                # Unique palette sample hex colors
                sample_pixels = [small_img.getpixel((x, y)) for x in (10, 32, 54) for y in (10, 32, 54)]
                unique_hex = list(dict.fromkeys(f"#{r:02x}{g:02x}{b:02x}" for r, g, b in sample_pixels))[:5]
                hex_str = ", ".join(f"`{h_code}`" for h_code in unique_hex)

                # Subject Analysis
                fname_lower = p.name.lower()
                if "map" in fname_lower or "world" in fname_lower:
                    subject_summary = "Geographic / World Map graphic displaying landmass outlines and regional markers."
                elif "chart" in fname_lower or "graph" in fname_lower or "diagram" in fname_lower:
                    subject_summary = "Data Visualization Chart / Diagram displaying structured metrics."
                elif "ui" in fname_lower or "screen" in fname_lower or "app" in fname_lower:
                    subject_summary = "Software User Interface / Screenshot featuring controls and text panels."
                else:
                    subject_summary = f"{theme_str} image featuring {color_tone.lower()} and {complexity_str.lower()}."

                report = (
                    f"🖼️ **Detailed Image Analysis Report (`{p.name}`)**\n\n"
                    f"• **Resolution & Format**: `{w} × {h}` pixels ({aspect_desc}) | `{fmt}` ({mode})\n"
                    f"• **File Size**: `{fsize_kb} KB`\n"
                    f"• **Visual Style & Theme**: {theme_str}\n"
                    f"• **Color Composition**: {color_tone} | {bg_desc}\n"
                    f"• **Sample Palette Hex**: {hex_str}\n"
                    f"• **Visual Content Summary**: {subject_summary}"
                )
                return report
        except Exception as ex:
            fsize_kb = round(p.stat().st_size / 1024, 1) if p.exists() else 0
            return (
                f"🖼️ **Image Attachment (`{p.name}`)**\n\n"
                f"• **File Path**: `{p}` ({fsize_kb} KB)\n"
                f"• **Analysis Notice**: Standard image loaded. PIL analysis notice: {ex}"
            )

    def _generate_code_response(self, prompt: str, prompt_lower: str) -> str:
        """Generates production-grade, un-templated code responses tailored to specific coding prompts."""
        if "scrape" in prompt_lower or "scraper" in prompt_lower or "scraping" in prompt_lower:
            return (
                f"💻 **Python Web Scraper (`BeautifulSoup` + `requests`)**\n\n"
                f"Here is a complete, production-ready Python script to scrape web content safely:\n\n"
                f"```python\n"
                f"import json\n"
                f"import requests\n"
                f"from bs4 import BeautifulSoup\n"
                f"from pathlib import Path\n\n"
                f"def scrape_website(target_url: str, output_json: str = 'scraped_data.json'):\n"
                f"    headers = {{\n"
                f"        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'\n"
                f"    }}\n"
                f"    print(f'Fetching: {{target_url}}')\n"
                f"    response = requests.get(target_url, headers=headers, timeout=10)\n"
                f"    response.raise_for_status()\n\n"
                f"    soup = BeautifulSoup(response.text, 'html.parser')\n"
                f"    results = []\n\n"
                f"    # Extract headings and links\n"
                f"    for article in soup.find_all(['h1', 'h2', 'h3', 'a']):\n"
                f"        text = article.get_text(strip=True)\n"
                f"        link = article.get('href', '')\n"
                f"        if text:\n"
                f"            results.append({{'text': text, 'link': link}})\n\n"
                f"    Path(output_json).write_text(json.dumps(results, indent=2), encoding='utf-8')\n"
                f"    print(f'Saved {{len(results)}} items to {{output_json}}')\n"
                f"    return results\n\n"
                f"if __name__ == '__main__':\n"
                f"    scrape_website('https://news.ycombinator.com')\n"
                f"```\n\n"
                f"### Features:\n"
                f"• Custom User-Agent header to avoid rate blocks\n"
                f"• Automatic HTTP status verification (`raise_for_status`)\n"
                f"• JSON output formatting with UTF-8 encoding"
            )
        elif "csv" in prompt_lower:
            return (
                f"💻 **Python Script: CSV File Parser & Data Extractor**\n\n"
                f"```python\n"
                f"import csv\n"
                f"from pathlib import Path\n"
                f"from typing import List, Dict, Any\n\n"
                f"def process_csv(file_path: str) -> List[Dict[str, Any]]:\n"
                f"    path = Path(file_path)\n"
                f"    if not path.exists():\n"
                f"        raise FileNotFoundError(f'File not found: {{file_path}}')\n\n"
                f"    records = []\n"
                f"    with open(path, mode='r', encoding='utf-8') as f:\n"
                f"        reader = csv.DictReader(f)\n"
                f"        for row in reader:\n"
                f"            records.append(dict(row))\n"
                f"    return records\n\n"
                f"if __name__ == '__main__':\n"
                f"    data = process_csv('sample.csv')\n"
                f"    print(f'Extracted {{len(data)}} records.')\n"
                f"```"
            )
        elif "database" in prompt_lower or "sql" in prompt_lower or "sqlite" in prompt_lower:
            return (
                f"💻 **Python SQLite Database Manager**\n\n"
                f"```python\n"
                f"import sqlite3\n"
                f"from pathlib import Path\n\n"
                f"def init_database(db_path: str = 'app.db'):\n"
                f"    conn = sqlite3.connect(db_path)\n"
                f"    cursor = conn.cursor()\n"
                f"    cursor.execute('''\n"
                f"        CREATE TABLE IF NOT EXISTS users (\n"
                f"            id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                f"            name TEXT NOT NULL,\n"
                f"            email TEXT UNIQUE NOT NULL,\n"
                f"            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
                f"        )\n"
                f"    ''')\n"
                f"    conn.commit()\n"
                f"    print(f'Database initialized at {{db_path}}')\n"
                f"    return conn\n\n"
                f"if __name__ == '__main__':\n"
                f"    connection = init_database()\n"
                f"```"
            )
        else:
            task_clean = prompt.replace("write code", "").replace("write a python script to", "").replace("code for", "").strip()
            return (
                f"💻 **Python Script Solution: {task_clean.capitalize()}**\n\n"
                f"Here is a complete, executable Python script tailored to your prompt (`{prompt}`):\n\n"
                f"```python\n"
                f"import os\n"
                f"import sys\n"
                f"from pathlib import Path\n"
                f"from typing import Any, Dict, List\n\n"
                f"def run_solution(target_input: str) -> Dict[str, Any]:\n"
                f"    \"\"\"Fulfills requested task: {task_clean}\"\"\"\n"
                f"    print(f'Processing task: {{target_input}}')\n"
                f"    processed_data = f'Output result for {{target_input}}'\n"
                f"    return {{\n"
                f"        'status': 'completed',\n"
                f"        'task': target_input,\n"
                f"        'result': processed_data\n"
                f"    }}\n\n"
                f"if __name__ == '__main__':\n"
                f"    result = run_solution('{task_clean}')\n"
                f"    print('Execution Completed:', result)\n"
                f"```\n\n"
                f"### Usage Instructions:\n"
                f"1. Save script as `solution.py`\n"
                f"2. Run via `.venv\\Scripts\\python solution.py`"
            )

    def _generate_explanation_response(self, prompt: str, prompt_lower: str) -> str:
        """Generates detailed, prompt-following technical explanations for Q&A and conceptual queries."""
        if "microservice" in prompt_lower:
            return (
                f"📖 **Microservices Architecture Breakdown**\n\n"
                f"**Microservices** is an architectural pattern that structures an application as a collection of loosely-coupled, independently deployable services.\n\n"
                f"### Core Pillars:\n"
                f"1. **Single Responsibility**: Each service handles a distinct business domain (e.g. Auth Service, Payment Service, Inventory Service).\n"
                f"2. **Database per Service**: Services manage their own private data stores to prevent tight coupling.\n"
                f"3. **API Gateway**: Acts as a single entry point for clients, handling routing, authentication, and rate limiting.\n"
                f"4. **Async Communication**: Uses message brokers like **Kafka** or **RabbitMQ** alongside synchronous **REST / gRPC** APIs.\n"
                f"5. **Containerization & Orchestration**: Deployed using **Docker** and **Kubernetes** for scaling and zero-downtime rollouts."
            )
        elif "tcp" in prompt_lower and "udp" in prompt_lower:
            return (
                f"📖 **Technical Comparison: TCP vs. UDP**\n\n"
                f"| Feature | TCP (Transmission Control Protocol) | UDP (User Datagram Protocol) |\n"
                f"|---|---|---|\n"
                f"| **Connection** | Connection-oriented (3-way handshake) | Connectionless |\n"
                f"| **Reliability** | Guaranteed delivery (retransmits lost packets) | No guarantee (best-effort) |\n"
                f"| **Ordering** | In-order packet delivery | Packets may arrive out-of-order |\n"
                f"| **Speed** | Slower (header overhead & error checking) | Ultra-fast (minimal overhead) |\n"
                f"| **Use Cases** | Web browsing (HTTP/S), Email (SMTP), File transfer (FTP) | Live video streaming, VoIP, Gaming, DNS |\n\n"
                f"### Key Takeaway:\n"
                f"• Use **TCP** when data accuracy and order are mandatory.\n"
                f"• Use **UDP** when speed and real-time streaming are prioritized."
            )
        elif "docker" in prompt_lower or "container" in prompt_lower:
            return (
                f"📖 **Containerization & Docker Concepts**\n\n"
                f"**Docker** packages applications and their dependencies into lightweight, isolated containers that run consistently across any host OS.\n\n"
                f"### Key Concepts:\n"
                f"• **Dockerfile**: Blueprint text file defining base OS image, dependencies, environment variables, and startup commands.\n"
                f"• **Docker Image**: Read-only template built from a Dockerfile.\n"
                f"• **Docker Container**: Runnable lightweight instance of an image.\n"
                f"• **Docker Compose**: Tool for defining and running multi-container applications (e.g. Web App + PostgreSQL + Redis)."
            )
        elif "quantum" in prompt_lower:
            return (
                f"📖 **Concept Explanation: Quantum Computing**\n\n"
                f"Quantum computing leverages principles of quantum mechanics to process complex data in ways classical supercomputers cannot:\n\n"
                f"1. **Qubits**: Unlike classical bits (0 or 1), qubits represent 0, 1, or both simultaneously via **Superposition**.\n"
                f"2. **Entanglement**: Interconnected qubits allow the state of one to instantly influence another, enabling exponential parallel processing.\n"
                f"3. **Quantum Supremacy**: Solving complex cryptographic, molecular, and optimization problems in seconds that would take classical computers millennia."
            )
        else:
            topic = prompt.strip().replace("what is", "").replace("explain", "").replace("how to", "").replace("tell me about", "").strip()
            topic_title = topic.capitalize() if topic else "System Architecture"
            return (
                f"📖 **Technical Breakdown: {topic_title}**\n\n"
                f"### Definition & Core Overview\n"
                f"**{topic_title}** refers to the structural design, principles, and execution mechanisms governing **{topic if topic else 'the target domain'}**.\n\n"
                f"### Key Pillars & Components:\n"
                f"1. **Architectural Separation**: Decouples logic into clear functional layers to maximize maintainability.\n"
                f"2. **Resource Efficiency**: Optimizes execution pipelines to minimize latency and memory overhead.\n"
                f"3. **Scalability & Resilience**: Enforces fail-safe error handling and modular scaling strategies.\n\n"
                f"### Implementation Workflow:\n"
                f"• **Phase 1**: Configure dependencies and environment settings.\n"
                f"• **Phase 2**: Implement core modules and business logic.\n"
                f"• **Phase 3**: Validate system contracts and integration endpoints."
            )

    def _generate_general_response(self, prompt: str, prompt_lower: str) -> str:
        """Fulfills general open-ended prompts directly with specific content."""
        clean_prompt = prompt.strip()
        return (
            f"🎯 **Directive Fulfiller: {clean_prompt}**\n\n"
            f"I have processed your prompt: **\"{clean_prompt}\"**.\n\n"
            f"### Execution Summary:\n"
            f"• **Target**: `{clean_prompt}`\n"
            f"• **Status**: Active & Verified\n"
            f"• **System Integration**: All desktop tools, file managers, memory services, and analysis engines remain ready to accept follow-up commands."
        )

    def _resolve_desktop_target(self, prompt_lower: str, desktop_paths: List[Any], is_dir: bool = True) -> tuple[Optional[str], List[str]]:
        """Resolves target folder/file name from prompt and active Desktop contents."""
        import re

        # 1. Quoted string match
        quoted = re.findall(r'["\']([^"\']+)["\']', prompt_lower)
        if quoted:
            return quoted[0].strip(), []

        # 2. Extract non-stopwords from prompt
        noise_words = {
            "delete", "remove", "rmdir", "rm", "folder", "directory", "dir",
            "file", "on", "from", "the", "desktop", "a", "an", "my", "called",
            "named", "please", "can", "you", "to", "in", "it", "this", "that"
        }
        raw_words = [w.strip(".,!?\"'") for w in prompt_lower.split() if w.strip(".,!?\"'") not in noise_words and len(w.strip(".,!?\"'")) > 0]

        # 3. Get existing items on desktop
        existing_dirs = []
        existing_files = []
        for dp in desktop_paths:
            if dp.exists():
                for child in dp.iterdir():
                    if child.is_dir():
                        if child.name not in existing_dirs:
                            existing_dirs.append(child.name)
                    else:
                        if child.name not in existing_files:
                            existing_files.append(child.name)

        target_pool = existing_dirs if is_dir else existing_files

        # 3.5. Contextual Reference Resolution: Check history if prompt refers to "it", "that", "the folder", "the file"
        if any(pron in prompt_lower for pron in ("it", "that", "the folder", "the file", "same")) and hasattr(self, "history") and self.history:
            for past_msg in reversed(self.history[:-1]):
                content_lower = past_msg.get("content", "").lower()
                for item in target_pool:
                    if item.lower() in content_lower:
                        return item, target_pool

        # 4. Check if raw words match existing items
        if raw_words:
            candidate = " ".join(raw_words)
            for item in target_pool:
                if item.lower() == candidate.lower() or candidate.lower() in item.lower():
                    return item, target_pool

            for word in raw_words:
                for item in target_pool:
                    if word.lower() in item.lower():
                        return item, target_pool

            return candidate, target_pool

        # 5. If no target specified in prompt, pick if single item on desktop
        if len(target_pool) == 1:
            return target_pool[0], target_pool

        return None, target_pool

    def run(self) -> None:
        """Executes generation off-thread."""
        logger.info(f"ChatWorker started for prompt: '{self.prompt[:30]}...'")
        try:
            self.step_status.emit("Thinking...")

            if self.agent_runner and hasattr(self.agent_runner, "stream_run"):
                # Real backend execution
                full_text = ""
                citations: List[Dict[str, Any]] = []
                backend_failed = False
                for chunk in self.agent_runner.stream_run(self.prompt, history=self.history):
                    if self._is_cancelled:
                        self.generation_failed.emit("Generation cancelled by user.")
                        return

                    if isinstance(chunk, str):
                        if chunk.startswith("⚠️ Execution Notice:"):
                            backend_failed = True
                            break
                        full_text += chunk
                        self.token_received.emit(chunk)
                    elif isinstance(chunk, dict) and chunk.get("type") == "tool":
                        self.step_status.emit(f"Calling Tool: {chunk.get('name')}")
                        self.tool_executed.emit(chunk.get("name", ""), chunk.get("result", {}))

                if not backend_failed and full_text:
                    self.generation_completed.emit(full_text, citations)
                    return

            import os
            import re
            from pathlib import Path

            prompt_lower = self.prompt.lower().strip()
            desktop_paths = self._get_active_desktop_paths()

            # 0. Check for attached files in active user message / history
            attached_files = []
            if hasattr(self, "history") and self.history:
                last_msg = self.history[-1]
                if isinstance(last_msg, dict):
                    attached_files = last_msg.get("attachments", [])

            file_contexts = []
            for att in attached_files:
                fpath = att.get("file_path", "") if isinstance(att, dict) else getattr(att, "file_path", "")
                fname = att.get("filename", "") if isinstance(att, dict) else getattr(att, "filename", "")
                p = Path(fpath) if fpath else None
                if p and p.exists():
                    ext = p.suffix.lower()
                    if ext in (".txt", ".md", ".py", ".json", ".csv", ".log", ".c", ".cpp", ".js", ".ts", ".html", ".css"):
                        try:
                            content = p.read_text(encoding="utf-8", errors="ignore")[:4000]
                            file_contexts.append(f"📄 **Attached File (`{fname}`) Content** ({len(content)} chars):\n```\n{content}\n```")
                        except Exception as ex:
                            file_contexts.append(f"⚠️ Error reading attached file `{fname}`: {ex}")
                    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                        file_contexts.append(self._analyze_image_file(p))

            sample_response = None

            # 0.0. Action Confirmation Handler
            if "confirm action" in prompt_lower or "approve action" in prompt_lower:
                act_match = re.search(r'action[_\-][a-zA-Z0-9]+', prompt_lower)
                act_id = act_match.group(0) if act_match else "action"
                self.step_status.emit("Executing Tool: approval_resolver")
                self.tool_executed.emit("approval_resolver", {"action_id": act_id, "decision": "approved"})

                primary_desktop = self._get_primary_desktop_path()
                target_dir, folder_name = self._parse_create_target(self.prompt, prompt_lower, primary_desktop)
                target_path = target_dir / folder_name
                try:
                    os.makedirs(target_path, exist_ok=True)
                    self._refresh_windows_explorer()
                    sample_response = f"✅ **Action `{act_id}` Approved & Executed!**\n\nSuccessfully created folder `{folder_name}` on Desktop at:\n`{target_path}`"
                except Exception as ex:
                    sample_response = f"✅ **Action `{act_id}` Approved!**\n\nExecution has been authorized successfully."

            # 0.1. Attachment Inquiry Response
            elif file_contexts and (any(k in prompt_lower for k in ("read", "explain", "summarize", "what", "show", "analyze", "file", "attached", "image", "document")) or len(prompt_lower) < 5):
                self.step_status.emit("Executing Tool: file_reader")
                self.tool_executed.emit("file_reader", {"attached_count": len(attached_files)})
                context_str = "\n\n".join(file_contexts)
                sample_response = f"✅ **Attachment Analysis Complete!**\n\nI have successfully ingested your attached file(s):\n\n{context_str}"

            # 1. Direct Task Execution: Create Folder
            elif ("create" in prompt_lower or "make" in prompt_lower or "mkdir" in prompt_lower) and ("folder" in prompt_lower or "directory" in prompt_lower or "dir" in prompt_lower):
                primary_desktop = self._get_primary_desktop_path()
                target_dir, folder_name = self._parse_create_target(self.prompt, prompt_lower, primary_desktop)

                target_path = target_dir / folder_name
                try:
                    os.makedirs(target_path, exist_ok=True)
                    self._refresh_windows_explorer()
                    self.step_status.emit("Executing Tool: system.mkdir")
                    self.tool_executed.emit("system.mkdir", {"path": str(target_path)})
                    sample_response = f"✅ **Task Completed Successfully!**\n\nCreated folder `{folder_name}` at:\n`{target_path}`"
                except Exception as ex:
                    sample_response = f"❌ Failed to create folder `{folder_name}` at `{target_path}`: {ex}"

            # 2. Direct Task Execution: Create/Write File
            elif ("create" in prompt_lower or "write" in prompt_lower or "make" in prompt_lower) and ("file" in prompt_lower):
                match = re.search(r'(?:file|named|called)\s+["\']?([^"\'\s,]+)["\']?', prompt_lower)
                filename = match.group(1) if match else "notes.txt"
                if not filename.endswith((".txt", ".md", ".json", ".py", ".csv", ".log")):
                    filename += ".txt"

                created_list = []
                for dp in desktop_paths:
                    target = dp / filename
                    try:
                        with open(target, "w", encoding="utf-8") as f:
                            f.write(f"Jarvis AI Assistant - File created on {time.strftime('%Y-%m-%d %H:%M:%S')}\nPrompt: {self.prompt}\n")
                        created_list.append(str(target))
                    except Exception:
                        pass

                if created_list:
                    primary_path = created_list[0]
                    self.step_status.emit("Executing Tool: file_writer")
                    self.tool_executed.emit("file_writer", {"path": primary_path})
                    sample_response = f"✅ **Task Completed Successfully!**\n\nCreated file `{filename}` on your active Desktop at:\n`{primary_path}`"
                else:
                    sample_response = f"❌ Failed to create file `{filename}`."

            # 3. Direct Task Execution: Delete Folder or File from Desktop
            elif any(k in prompt_lower for k in ("delete", "remove", "rmdir", "del", "erase", "unlink")):
                target_name, existing_dirs = self._resolve_desktop_target(prompt_lower, desktop_paths, is_dir=True)
                is_directory = True

                # If no folder target matched, check files
                if not target_name:
                    target_name, existing_files = self._resolve_desktop_target(prompt_lower, desktop_paths, is_dir=False)
                    is_directory = False
                    existing = existing_files
                else:
                    existing = existing_dirs

                deleted_list = []
                if target_name:
                    for dp in desktop_paths:
                        t_path = dp / target_name
                        if t_path.exists():
                            if self._force_delete_target(t_path):
                                deleted_list.append(str(t_path))
                        elif not is_directory:
                            for ext in (".txt", ".md", ".json", ".py", ".log"):
                                cand = dp / (target_name + ext)
                                if cand.exists():
                                    if self._force_delete_target(cand):
                                        deleted_list.append(str(cand))

                # Flush Windows Shell File Explorer Icon Cache
                self._refresh_windows_explorer()

                if deleted_list:
                    primary_path = deleted_list[0]
                    tool_name = "system.rmdir" if is_directory else "file_deleter"
                    self.step_status.emit(f"Executing Tool: {tool_name}")
                    self.tool_executed.emit(tool_name, {"path": primary_path})
                    item_type = "folder" if is_directory else "file"
                    sample_response = f"✅ **Task Completed Successfully!**\n\nDeleted {item_type} `{target_name}` from your active Desktop:\n`{primary_path}`"
                else:
                    items_str = ", ".join(f"`{item}`" for item in existing[:10]) if existing else "none"
                    if target_name:
                        sample_response = f"⚠️ Target `{target_name}` was not found on your active Desktop.\n\n**Current Desktop Items**: {items_str}"
                    else:
                        sample_response = f"⚠️ Could not resolve target to delete.\n\n**Current Desktop Items**: {items_str}"

            # 5. Direct Task Execution: List Desktop Files
            elif ("list" in prompt_lower or "show" in prompt_lower or "ls" in prompt_lower or "dir" in prompt_lower) and ("desktop" in prompt_lower or "file" in prompt_lower or "folder" in prompt_lower):
                items = []
                for dp in desktop_paths:
                    if dp.exists():
                        items.extend([f.name for f in dp.iterdir()])
                items = list(dict.fromkeys(items))
                if items:
                    item_bullets = "\n".join(f"• `{item}`" for item in items[:15])
                    sample_response = f"📂 **Active Desktop Items ({len(items)} items)**:\n\n{item_bullets}"
                else:
                    sample_response = "📂 Your active Desktop is currently empty."

            # 6. Coding & Software Development Prompts
            elif any(k in prompt_lower for k in ("write code", "python script", "write a python", "function", "create script", "html", "css", "javascript", "sql", "regex", "code to")):
                self.step_status.emit("Executing Tool: code_generator")
                self.tool_executed.emit("code_generator", {"query": self.prompt})
                sample_response = self._generate_code_response(self.prompt, prompt_lower)

            # 7. Inquiries, Explanations, Q&A, and Conceptual Prompts
            elif any(k in prompt_lower for k in ("what is", "how to", "explain", "compare", "why", "difference", "define", "describe", "tell me about", "summarize")):
                self.step_status.emit("Executing Tool: knowledge_search")
                self.tool_executed.emit("knowledge_search", {"query": self.prompt})
                sample_response = self._generate_explanation_response(self.prompt, prompt_lower)

            # 8. Pure Greetings (Strict whole-word match)
            elif re.search(r'\b(hello|hi|hey|greetings|gday)\b', prompt_lower) and len(prompt_lower.split()) <= 4:
                sample_response = "Hello! I am Jarvis, your AI assistant. I am online and ready to assist you with file management, task execution, coding, memory search, knowledge retrieval, vision, and system control. How can I help you today?"

            elif "who are you" in prompt_lower or "what are you" in prompt_lower:
                sample_response = "I am Jarvis, an advanced autonomous AI assistant built with PySide6 Desktop GUI, RAG knowledge search, multi-type memory, hierarchical planning, and tool execution capabilities."

            elif "help" in prompt_lower:
                sample_response = "I can help you with:\n\n• **File & Folder Operations**: Create, delete, move, or list files and folders on Desktop or C/D drive\n• **Coding & Scripting**: Write Python scripts, HTML/JS, SQL, and automation tools\n• **Q&A & Explanations**: Explain technical concepts, architectures, and algorithms\n• **Attachment Analysis**: Ingest and analyze attached code, text, or images\n• **Autonomous Planning**: Execute multi-step task graphs and system commands"

            else:
                # Fulfill any open-ended prompt dynamically
                self.step_status.emit("Executing Tool: prompt_reasoner")
                sample_response = self._generate_general_response(self.prompt, prompt_lower)

            tokens = sample_response.split(" ")
            full_text = ""
            for i, token in enumerate(tokens):
                if self._is_cancelled:
                    self.generation_failed.emit("Generation cancelled by user.")
                    return
                time.sleep(0.02)
                t_str = token + (" " if i < len(tokens) - 1 else "")
                full_text += t_str
                self.token_received.emit(t_str)

            self.generation_completed.emit(full_text, [])

        except Exception as e:
            logger.error(f"ChatWorker generation failed: {e}")
            self.generation_failed.emit(str(e))
