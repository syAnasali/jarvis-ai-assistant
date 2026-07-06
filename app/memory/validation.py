"""Deterministic evidence validation for long-term memory candidates."""

import re
from app.memory.models import MemoryCandidate, MemoryType


class MemoryEvidenceValidator:
    """Verifies that memory candidates have exact supporting verbatim evidence in the source text."""

    # First-person reference indicators (case-insensitive)
    FIRST_PERSON_PAT = re.compile(
        r"\b(i|my|me|myself|we|our|ours|us|i'm|im|i've|ive|i'd|id|i'll|ill)\b",
        re.IGNORECASE
    )

    # General preference indicators
    PREF_INDICATORS = {
        "prefer", "prefers", "preferred", "preference", "preferring",
        "like", "likes", "liked", "liking", "love", "loves", "loved", "loving",
        "usually", "always", "habit", "habits", "default", "defaults",
        "style", "favor", "favors", "favored", "favoring",
        "opt", "opts", "opted", "opting", "choose", "chooses", "chose", "choosing", "choice", "choices",
        "hate", "hates", "hated", "hating", "dislike", "dislikes", "disliked", "disliking",
        "enjoy", "enjoys", "enjoyed", "enjoying",
        "desire", "desires", "desired", "want", "wants", "wanted", "wanting",
        "wish", "wishes", "wished", "wishing", "tend to", "tends to", "tended to",
        "customarily", "frequently", "seldom"
    }

    # General project indicators
    PROJECT_INDICATORS = {
        "build", "builds", "built", "building",
        "develop", "develops", "developed", "developing", "development",
        "work", "works", "worked", "working", "work on", "works on", "working on",
        "maintain", "maintains", "maintained", "maintaining",
        "plan", "plans", "planned", "planning",
        "pursue", "pursues", "pursued", "pursuing",
        "project", "projects",
        "create", "creates", "created", "creating",
        "write", "writes", "wrote", "writing",
        "code", "codes", "coded", "coding",
        "make", "makes", "made", "making",
        "design", "designs", "designed", "designing",
        "author", "authors", "authored", "authoring"
    }

    # General educational/study indicators
    EDU_INDICATORS = {
        "study", "studies", "studied", "studying",
        "learn", "learns", "learned", "learning",
        "prepare", "prepares", "prepared", "preparing", "prepare for", "prepares for", "preparing for",
        "enroll", "enrolls", "enrolled", "enrolling",
        "student", "students", "major", "majors", "majoring",
        "take", "takes", "took", "taking", "course", "courses", "class", "classes", "program", "programs"
    }

    # Imperative/request starter verbs
    IMPERATIVE_VERBS = {
        "write", "create", "build", "explain", "generate", "fix", "solve", "implement",
        "run", "check", "find", "get", "add", "list", "show", "tell", "make", "do",
        "help", "answer", "respond", "can", "could", "would", "please", "should"
    }

    def validate(self, candidate: MemoryCandidate, source_text: str) -> bool:
        """Determines if candidate evidence is valid and explicitly supports the candidate claim.

        Args:
            candidate: The MemoryCandidate to validate.
            source_text: The original user request message.

        Returns:
            bool: True if the candidate is validated, False if rejected.
        """
        evidence = candidate.evidence
        if not evidence or not isinstance(evidence, str) or not evidence.strip():
            return False

        if not source_text or not isinstance(source_text, str) or not source_text.strip():
            return False

        # Whitespace normalization check
        norm_evidence = re.sub(r"\s+", " ", evidence.strip().lower())
        norm_source = re.sub(r"\s+", " ", source_text.strip().lower())

        # 1. Verification of verbatim presence
        # Case behavior: Case-insensitive verbatim presence check for robustness,
        # but matching exact word boundaries/sequence after whitespace normalization.
        if norm_evidence not in norm_source:
            return False

        # 2. Claim-Support Conservatism (Part 5)
        # Verify that candidate claims are explicitly supported by first-person evidence
        # to distinguish them from task-local commands (e.g. "Create...", "Write...").
        has_first_person = bool(self.FIRST_PERSON_PAT.search(evidence))

        # Enforce first-person reference for ALL memory candidates to avoid task-local inferences
        if not has_first_person:
            return False

        # Reject if evidence starts with an imperative verb or request starter (e.g. Can you...)
        first_word = norm_evidence.split()[0] if norm_evidence.split() else ""
        first_word = re.sub(r"^\W+|\W+$", "", first_word)
        if first_word in self.IMPERATIVE_VERBS:
            return False

        # Check by MemoryType
        if candidate.memory_type == MemoryType.PREFERENCE:
            # Must have explicit preference word
            words = set(re.findall(r"\b\w+\b", norm_evidence))
            if not words.intersection(self.PREF_INDICATORS):
                return False

        elif candidate.memory_type == MemoryType.PROJECT:
            # Must have explicit project word
            words = set(re.findall(r"\b\w+\b", norm_evidence))
            if not words.intersection(self.PROJECT_INDICATORS):
                return False

        # 3. educational context check (e.g., studying, learning)
        content_lower = candidate.content.lower()
        if "study" in content_lower or "learn" in content_lower or "studying" in content_lower:
            # Verify evidence contains education indicators
            words = set(re.findall(r"\b\w+\b", norm_evidence))
            if not words.intersection(self.EDU_INDICATORS):
                return False

        return True
