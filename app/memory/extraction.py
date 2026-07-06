"""LLM-based memory extraction implementation."""

from typing import Dict, Any, List
from app.core.exceptions import MemoryExtractionError, LLMError
from app.ai.manager import LLMManager
from app.ai.models import GenerationProfile
from app.ai.prompts import PromptManager
from app.ai.parser import ResponseParser
from app.memory.interfaces import MemoryExtractor
from app.memory.models import MemoryExtractionResult, MemorySource
from app.memory.parser import MemoryExtractionParser


class LLMMemoryExtractor(MemoryExtractor):
    """Extracts structured memories from raw text using the active LLM provider."""

    def __init__(self, llm_manager: LLMManager, prompt_manager: PromptManager | None = None) -> None:
        """Initializes the LLMMemoryExtractor.

        Args:
            llm_manager: Active LLMManager instance.
            prompt_manager: Optional PromptManager instance.
        """
        self._llm_manager = llm_manager
        self._prompt_manager = prompt_manager or PromptManager()
        self._parser = MemoryExtractionParser()
        self._response_parser = ResponseParser()

    def extract(self, text: str) -> MemoryExtractionResult:
        """Extracts candidate memory records from raw text.

        Args:
            text: The raw user message text.

        Returns:
            MemoryExtractionResult: Extracted candidates and source details.

        Raises:
            MemoryExtractionError: If extraction fails or response parsing fails.
        """
        if not text or not text.strip():
            return MemoryExtractionResult(candidates=(), source_text=text, candidate_count=0)

        system_instruction = self._prompt_manager.memory_extraction_prompt()
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"USER MESSAGE:\n{text}"}
        ]

        try:
            # Execute generation using the MEMORY_EXTRACTION profile
            gen_result = self._llm_manager.generate(
                messages=messages,
                profile=GenerationProfile.MEMORY_EXTRACTION
            )

            # Parse completion response text
            parsed_resp = self._response_parser.parse_response(gen_result.raw_response)
            completion_text = parsed_resp.text

            # Parse JSON memories array into MemoryCandidate list
            candidates = self._parser.parse(completion_text, source=MemorySource.USER)

            return MemoryExtractionResult(
                candidates=tuple(candidates),
                source_text=text,
                candidate_count=len(candidates)
            )

        except LLMError as le:
            raise MemoryExtractionError(f"LLM generation failed during memory extraction: {le}") from le
        except Exception as e:
            if isinstance(e, MemoryExtractionError):
                raise e
            raise MemoryExtractionError(f"Unexpected error during memory extraction: {e}") from e
