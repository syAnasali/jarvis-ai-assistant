"""Narrow deterministic secret guard utilities."""

import re

# Patterns to match obvious secret/credential forms
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN\s+[A-Z0-9\s_]+-----", re.IGNORECASE)
BEARER_TOKEN_PATTERN = re.compile(r"(bearer\s+[a-z0-9\-_\.\~]+|authorization:\s*bearer\s+)", re.IGNORECASE)
COMMON_API_TOKEN_PATTERN = re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,}|github_pat_[a-zA-Z0-9_]{20,})\b", re.IGNORECASE)
PASSWORD_ASSIGNMENT_PATTERN = re.compile(r"\b(password|passwd|passcode|secret)\s*(=|:|is)\s*\S+", re.IGNORECASE)


class SecretGuard:
    """Performs deterministic pattern matching to reject storing sensitive credentials as memories."""

    def contains_secret(self, content: str) -> bool:
        """Determines if the content contains obvious secrets like keys, bearer tokens, or passwords.

        Args:
            content: The text content to verify.

        Returns:
            bool: True if an obvious secret is detected, False otherwise.
        """
        if not content:
            return False

        if PRIVATE_KEY_PATTERN.search(content):
            return True
        if BEARER_TOKEN_PATTERN.search(content):
            return True
        if COMMON_API_TOKEN_PATTERN.search(content):
            return True
        if PASSWORD_ASSIGNMENT_PATTERN.search(content):
            return True

        return False
