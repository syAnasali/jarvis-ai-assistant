"""Robust JSON parser for LLM memory extraction responses."""

import json
import re
from typing import List
from app.core.exceptions import MemoryExtractionError
from app.memory.models import MemoryCandidate, MemoryType, MemorySource


class MemoryExtractionParser:
    """Parses LLM model outputs into validated MemoryCandidate domain objects."""

    def parse(self, raw_text: str, source: MemorySource = MemorySource.USER) -> List[MemoryCandidate]:
        """Parses LLM response string expecting JSON format into valid MemoryCandidates.

        Args:
            raw_text: Raw LLM text response.
            source: Default MemorySource to assign to candidates.

        Returns:
            List[MemoryCandidate]: List of parsed valid candidates.

        Raises:
            MemoryExtractionError: If top-level JSON structure or parsing fails.
        """
        text = raw_text.strip()
        # Strip potential markdown wrapper blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise MemoryExtractionError(f"Invalid JSON format returned by LLM: {e}") from e

        if not isinstance(data, dict):
            raise MemoryExtractionError("Top-level LLM memory extraction response must be a JSON object.")

        if "memories" not in data:
            raise MemoryExtractionError("Missing required top-level key 'memories'.")

        memories_list = data["memories"]
        if not isinstance(memories_list, list):
            raise MemoryExtractionError("'memories' key must map to a JSON array/list.")

        candidates = []
        for item in memories_list:
            if not isinstance(item, dict):
                # Skip individual entries that are not JSON objects
                continue

            try:
                content = item.get("content")
                if not content or not isinstance(content, str) or not content.strip():
                    continue

                # Normalize content whitespaces (remove repeated internal spaces)
                normalized_content = re.sub(r"\s+", " ", content.strip())

                type_str = item.get("memory_type")
                if not type_str or not isinstance(type_str, str):
                    continue

                try:
                    memory_type = MemoryType[type_str.upper()]
                except KeyError:
                    # Skip unknown memory type strings
                    continue

                importance_val = item.get("importance", 0.5)
                confidence_val = item.get("confidence", 1.0)

                # Construct MemoryCandidate, catching any validation errors
                candidates.append(
                    MemoryCandidate(
                        content=normalized_content,
                        memory_type=memory_type,
                        importance=float(importance_val),
                        confidence=float(confidence_val),
                        source=source,
                        metadata={}
                    )
                )
            except Exception:
                # Skip individual malformed items to preserve valid sibling entries
                continue

        return candidates
