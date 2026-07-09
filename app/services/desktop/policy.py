"""Policy rules, canonicalization, and parameter validators for desktop interactions."""

from typing import List, Tuple, Union, Set
from app.core.exceptions import (
    InvalidTextError,
    TextTooLongError,
    InvalidKeyError,
    InvalidHotkeyError,
    InvalidCoordinatesError,
    UnsupportedButtonError,
)

# Centralized strict key allowlist
ALLOWED_KEYS: Set[str] = {
    "enter",
    "tab",
    "escape",
    "backspace",
    "delete",
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
}

# Strict hotkey combinations allowlist (stored as canonical tuples)
ALLOWED_HOTKEYS: Set[Tuple[str, ...]] = {
    ("ctrl", "c"),
    ("ctrl", "v"),
    ("ctrl", "x"),
    ("ctrl", "z"),
    ("ctrl", "y"),
    ("ctrl", "a"),
    ("ctrl", "s"),
    ("ctrl", "f"),
    ("ctrl", "n"),
    ("ctrl", "o"),
    ("alt", "f4"),
}


class DesktopPolicy:
    """Enforces boundaries and security rules for user input automation."""

    @staticmethod
    def validate_text(text: str, max_chars: int) -> None:
        """Validates typed text content constraints.

        Raises:
            InvalidTextError: If invalid characters like null bytes are found.
            TextTooLongError: If the text length exceeds the limit.
        """
        if not isinstance(text, str):
            raise InvalidTextError("Input text must be a string.")

        if "\x00" in text:
            raise InvalidTextError("NUL bytes are strictly prohibited in input text.")

        if len(text) > max_chars:
            raise TextTooLongError(f"Input text exceeds maximum allowed length of {max_chars} characters.")

    @staticmethod
    def validate_key(key: str) -> None:
        """Validates that the key is in the strict allowlist.

        Raises:
            InvalidKeyError: If the key is unsupported or unsafe.
        """
        if not isinstance(key, str):
            raise InvalidKeyError("Key name must be a string.")

        normalized_key = key.strip().lower()
        if normalized_key not in ALLOWED_KEYS:
            raise InvalidKeyError(
                f"Key '{key}' is not allowed. Allowed keys: {sorted(list(ALLOWED_KEYS))}"
            )

    @classmethod
    def canonicalize_hotkey(cls, keys: Union[str, List[str]]) -> List[str]:
        """Normalizes and validates a hotkey combination.

        Accepts either a string like "ctrl+c" or a list of keys like ["Ctrl", "C"].
        Normalizes modifiers ("control" -> "ctrl").
        Detects duplicates and unsupported modifiers.

        Raises:
            InvalidHotkeyError: If validation fails.
        """
        if isinstance(keys, str):
            parts = [p.strip() for p in keys.split("+")]
        elif isinstance(keys, list):
            parts = [str(p).strip() for p in keys]
        else:
            raise InvalidHotkeyError("Hotkey format must be a list of keys or a '+' separated string.")

        if not parts or any(not p for p in parts):
            raise InvalidHotkeyError("Empty key found in hotkey combination.")

        # Normalize modifier names and map to lower case
        normalized = []
        for key in parts:
            k = key.lower()
            if k == "control":
                k = "ctrl"
            normalized.append(k)

        # Detect duplicates
        if len(normalized) != len(set(normalized)):
            raise InvalidHotkeyError("Duplicate keys are prohibited in hotkey combination.")

        # Validate combination against strict allowlist
        hotkey_tuple = tuple(normalized)
        if hotkey_tuple not in ALLOWED_HOTKEYS:
            raise InvalidHotkeyError(
                f"Hotkey combination '{keys}' is not permitted. "
                "Allowed combinations: ctrl+c, ctrl+v, ctrl+x, ctrl+z, ctrl+y, ctrl+a, ctrl+s, ctrl+f, ctrl+n, ctrl+o, alt+f4."
            )

        return normalized

    @staticmethod
    def validate_coordinates(x: int, y: int, screen_width: int, screen_height: int) -> None:
        """Validates coordinate bounds.

        Raises:
            InvalidCoordinatesError: If coordinates are out-of-bounds.
        """
        # Enforce integers
        if not isinstance(x, int) or not isinstance(y, int) or isinstance(x, bool) or isinstance(y, bool):
            raise InvalidCoordinatesError("Coordinates must be integers.")

        if x < 0 or y < 0:
            raise InvalidCoordinatesError(f"Coordinates cannot be negative: ({x}, {y})")

        if x >= screen_width or y >= screen_height:
            raise InvalidCoordinatesError(
                f"Coordinates ({x}, {y}) are outside the current virtual screen bounds: ({screen_width}x{screen_height})"
            )

    @staticmethod
    def validate_button(button: str) -> str:
        """Validates click button constraint.

        Raises:
            UnsupportedButtonError: If the button is not left or right.
        """
        if not isinstance(button, str):
            raise UnsupportedButtonError("Button name must be a string.")

        normalized_btn = button.strip().lower()
        if normalized_btn not in {"left", "right"}:
            raise UnsupportedButtonError(f"Button '{button}' is unsupported. Only 'left' or 'right' allowed.")

        return normalized_btn
