"""Centralized ID generation utilities."""

import uuid


def generate_request_id() -> str:
    """Generates a unique request identifier.

    Returns:
        str: Generated request identifier.
    """
    return f"req_{uuid.uuid4().hex[:8]}"


def generate_message_id() -> str:
    """Generates a unique message identifier.

    Returns:
        str: Generated message identifier.
    """
    return f"msg_{uuid.uuid4().hex[:8]}"


def generate_response_id() -> str:
    """Generates a unique response identifier.

    Returns:
        str: Generated response identifier.
    """
    return f"resp_{uuid.uuid4().hex[:8]}"


def generate_memory_id() -> str:
    """Generates a unique memory identifier.

    Returns:
        str: Generated memory identifier.
    """
    return f"mem_{uuid.uuid4().hex[:8]}"
