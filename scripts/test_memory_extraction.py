"""Diagnostic to test LLM-based memory extraction."""

import os
import sys
import tempfile
from pathlib import Path

# Add root folder to python path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from app.config.settings import settings
from app.core.logger import JarvisLogger
from app.ai.manager import LLMManager
from app.ai.providers.ollama import OllamaProvider
from app.memory.extraction import LLMMemoryExtractor

# Configure logging
JarvisLogger.get_logger("agent_controller")


def main():
    print("============================================================")
    print("Memory Extraction Diagnostic")
    print("Method: LLM-based extraction")
    print("Results may vary by local model (Active model: qwen3:8b)")
    print("============================================================\n")

    # Setup LLMManager and OllamaProvider
    llm_manager = LLMManager()
    ollama_provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
    llm_manager.register_provider("ollama", ollama_provider)
    llm_manager.load_provider("ollama")

    extractor = LLMMemoryExtractor(llm_manager=llm_manager)

    test_inputs = [
        "My name is Anas.",
        "I prefer Python for personal projects.",
        "I am building a local AI assistant called Jarvis.",
        "I study computer science.",
        "Hello.",
        "Thanks.",
        "What time is it?",
        "Explain photosynthesis.",
        "Write a Python function to reverse a string."
    ]

    inputs_tested = 0
    inputs_with_memories = 0
    total_candidates = 0
    no_memory_inputs_empty = 0

    for text in test_inputs:
        print(f"Input: '{text}'")
        inputs_tested += 1

        try:
            result = extractor.extract(text)
            candidates = result.candidates
            print(f"  Candidate count: {result.candidate_count}")
            
            if result.candidate_count > 0:
                inputs_with_memories += 1
                for cand in candidates:
                    total_candidates += 1
                    print(f"  - Content   : '{cand.content}'")
                    print(f"    Type      : {cand.memory_type.value}")
                    print(f"    Importance: {cand.importance}")
                    print(f"    Confidence: {cand.confidence}")
            else:
                no_memory_inputs_empty += 1
                print("  (No candidate memories extracted)")
        except Exception as e:
            print(f"  Error extracting memories: {e}")
        print()

    print("============================================================")
    print("Memory Extraction Diagnostic Summary")
    print("============================================================")
    print(f"Inputs tested                : {inputs_tested}")
    print(f"Inputs with memories         : {inputs_with_memories}")
    print(f"Total candidates             : {total_candidates}")
    print(f"No-memory inputs empty count : {no_memory_inputs_empty}")
    print("============================================================\n")


if __name__ == "__main__":
    main()
