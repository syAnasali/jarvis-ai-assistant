"""LLM-based memory conflict resolver implementation."""

import json
from typing import List

from app.ai.manager import LLMManager
from app.ai.models import GenerationProfile
from app.ai.scheduler import InferencePriority
from app.memory.interfaces import MemoryResolver
from app.memory.models import Memory, MemoryCandidate
from app.memory.resolution import MemoryResolutionDecision, MemoryResolutionParser, MemoryResolutionAction
from app.core.logger import JarvisLogger


class LLMMemoryResolver(MemoryResolver):
    """Memory conflict resolver using the LLM to classify and validate candidate updates."""

    def __init__(self, llm_manager: LLMManager) -> None:
        """Initializes the LLMMemoryResolver.

        Args:
            llm_manager: Injected LLMManager for coordinating models.
        """
        self._llm_manager = llm_manager
        self._logger = JarvisLogger.get_logger("memory_resolver")

    def resolve(self, candidate: MemoryCandidate, related_memories: List[Memory]) -> MemoryResolutionDecision:
        """Invokes the LLM to determine conflict resolution for a candidate against related memories.

        Args:
            candidate: The MemoryCandidate being evaluated.
            related_memories: List of potentially related memories.

        Returns:
            MemoryResolutionDecision: Resolution action and metadata.
        """
        if not related_memories:
            # Short-circuit: no related memories means we can directly CREATE
            return MemoryResolutionDecision(
                action=MemoryResolutionAction.CREATE,
                candidate=candidate,
                target_memory_id=None,
                confidence=1.0,
                reason_code="NO_RELATED_MEMORY",
            )

        # Format prompt
        prompt = self._build_prompt(candidate, related_memories)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise database conflict resolution subsystem. "
                    "Your task is to analyze a new candidate memory against existing related memories "
                    "and output a single JSON object deciding the correct resolution action. "
                    "Do NOT output any markdown code blocks, reasoning prose, or explanations. Only output raw JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            self._logger.debug(f"Submitting memory resolution request for candidate: '{candidate.content}'")
            result = self._llm_manager.generate(
                messages=messages,
                profile=GenerationProfile.MEMORY_RESOLUTION,
                priority=InferencePriority.MEMORY_RESOLUTION
            )
            response_text = result.raw_response
            if isinstance(response_text, dict):
                # If provider returns parsed dict or ChatResponse
                response_text = response_text.get("message", {}).get("content", "")
            elif not isinstance(response_text, str):
                response_text = str(response_text)

            self._logger.debug(f"Resolver raw response: {response_text.strip()}")
            decision = MemoryResolutionParser.parse(response_text, candidate)
            self._logger.info(
                f"Resolved candidate: action={decision.action.value}, "
                f"target={decision.target_memory_id}, conf={decision.confidence:.2f}, "
                f"code={decision.reason_code}"
            )
            return decision

        except Exception as e:
            self._logger.error(f"LLM memory resolution failed: {e}")
            # Safe conservative fallback on failure: IGNORE the candidate to prevent destructive updates
            return MemoryResolutionDecision(
                action=MemoryResolutionAction.IGNORE,
                candidate=candidate,
                target_memory_id=None,
                confidence=0.0,
                reason_code="UNSUPPORTED_RESOLUTION"
            )

    def _build_prompt(self, candidate: MemoryCandidate, related_memories: List[Memory]) -> str:
        """Constructs the prompt for conflict resolution classification."""
        related_str = ""
        for i, mem in enumerate(related_memories):
            related_str += (
                f"- ID: {mem.memory_id}\n"
                f"  Content: \"{mem.content}\"\n"
                f"  Type: {mem.memory_type.value}\n"
                f"  Importance: {mem.importance}\n\n"
            )

        prompt = (
            "Analyze this new Candidate memory (extracted from the user's latest statement) against the existing "
            "Related memories stored in the database. Decide the action that must be taken.\n\n"
            
            f"Candidate Memory:\n"
            f"- Content: \"{candidate.content}\"\n"
            f"- Type: {candidate.memory_type.value}\n"
            f"- Evidence: \"{candidate.evidence}\"\n\n"
            
            f"Existing Related Memories:\n"
            f"{related_str}"
            
            "Determine the correct action and output a JSON object with these fields:\n"
            "- \"action\": One of: \"CREATE\", \"UPDATE\", \"REPLACE\", \"KEEP_BOTH\", \"IGNORE\".\n"
            "- \"target_memory_id\": The ID of the existing memory that conflicts/matches, or null.\n"
            "- \"confidence\": A score from 0.0 to 1.0 representing your classification confidence.\n"
            "- \"reason_code\": A short code matching one of these categories:\n"
            "  * \"NO_RELATED_MEMORY\": No related memory exists (use with CREATE).\n"
            "  * \"SAME_DURABLE_CLAIM\": Candidate is already fully represented by an existing memory (use with IGNORE).\n"
            "  * \"UPDATED_PREFERENCE\": Candidate is a newer preference replacing/updating an old preference (use with UPDATE).\n"
            "  * \"UPDATED_FACT\": Candidate is a newer fact updating an old fact (use with UPDATE).\n"
            "  * \"CHANGED_STATE\": Candidate replaces a previous state that is now obsolete (e.g. moved, graduated) (use with REPLACE).\n"
            "  * \"DISTINCT_SCOPE\": Memories are related but describe different scopes (e.g. Next.js for web vs Python for AI) (use with KEEP_BOTH).\n"
            "  * \"DISTINCT_PROJECT\": Memories are different active projects/tasks (use with KEEP_BOTH).\n"
            "  * \"UNSUPPORTED_RESOLUTION\": Fallback/error code.\n\n"
            
            "CRITICAL RULES:\n"
            "1. Different scoped preferences (e.g. Next.js for web, Python for AI) or different active projects must NOT conflict; use KEEP_BOTH.\n"
            "2. Do not treat shared nouns or same memory types alone as conflicts. Only conflict if they describe the exact same preference/fact dimension.\n"
            "3. If candidate content matches existing content exactly or semantically, use IGNORE and SAME_DURABLE_CLAIM.\n"
            "4. UPDATE or REPLACE require a valid target_memory_id from the related list. CREATE must have target_memory_id set to null.\n"
            "5. If you are uncertain of a conflict, prefer KEEP_BOTH or IGNORE to avoid destructive deletion of correct data.\n\n"
            
            "Return ONLY the raw JSON object. Do not include markdown code block formatting, explanations, or reasoning."
        )
        return prompt
