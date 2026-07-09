"""Diagnostic script to verify desktop interaction policy constraints and parameter validation."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.desktop.policy import DesktopPolicy
from app.core.exceptions import (
    InvalidTextError,
    TextTooLongError,
    InvalidKeyError,
    InvalidHotkeyError,
    InvalidCoordinatesError,
    UnsupportedButtonError,
)


def run_diagnostics() -> bool:
    print("=== Running Desktop Policy & Validation Diagnostics ===")
    policy = DesktopPolicy()
    success = True

    # 1. Text typing validations
    print("\nTest 1: Text typing validation...")
    try:
        # A. NUL byte check
        try:
            policy.validate_text("Hello\x00Anas", max_chars=100)
            print("  [FAIL] Text with NUL byte was not rejected.")
            success = False
        except InvalidTextError as e:
            print(f"  [PASS] NUL byte text correctly rejected: {e}")

        # B. Text length check
        try:
            policy.validate_text("A" * 101, max_chars=100)
            print("  [FAIL] Text exceeding max length was not rejected.")
            success = False
        except TextTooLongError as e:
            print(f"  [PASS] Text length exceeded correctly rejected: {e}")

        # C. Valid text
        policy.validate_text("Valid text string", max_chars=100)
        print("  [PASS] Valid text input validated successfully.")

    except Exception as e:
        print(f"  [FAIL] Unexpected error during text validation: {e}")
        success = False

    # 2. Key allowlist validations
    print("\nTest 2: Key allowlist validation...")
    try:
        # A. Valid key
        policy.validate_key("enter")
        policy.validate_key("escape")
        print("  [PASS] Allowed keys validated successfully.")

        # B. Invalid key
        try:
            policy.validate_key("win")
            print("  [FAIL] Forbidden key 'win' was not rejected.")
            success = False
        except InvalidKeyError as e:
            print(f"  [PASS] Forbidden key correctly rejected: {e}")

        # C. Function key rejection
        try:
            policy.validate_key("f5")
            print("  [FAIL] Function key 'f5' was not rejected.")
            success = False
        except InvalidKeyError as e:
            print(f"  [PASS] Function key correctly rejected: {e}")

    except Exception as e:
        print(f"  [FAIL] Unexpected error during key validation: {e}")
        success = False

    # 3. Hotkey shortcut canonicalization
    print("\nTest 3: Hotkey combination canonicalization...")
    try:
        # A. Normalization of modifier
        canon1 = policy.canonicalize_hotkey("Control+S")
        if canon1 == ["ctrl", "s"]:
            print("  [PASS] Modifier normalization (Control -> ctrl) succeeded.")
        else:
            print(f"  [FAIL] Normalization failed. Got {canon1}")
            success = False

        # B. Canonicalize list
        canon2 = policy.canonicalize_hotkey(["Ctrl", "C"])
        if canon2 == ["ctrl", "c"]:
            print("  [PASS] List canonicalization succeeded.")
        else:
            print(f"  [FAIL] List canonicalization failed. Got {canon2}")
            success = False

        # C. Duplicate key rejection
        try:
            policy.canonicalize_hotkey("ctrl+ctrl+s")
            print("  [FAIL] Duplicate keys in hotkey were not rejected.")
            success = False
        except InvalidHotkeyError as e:
            print(f"  [PASS] Duplicate keys correctly rejected: {e}")

        # D. Unallowed hotkey rejection
        try:
            policy.canonicalize_hotkey("ctrl+alt+del")
            print("  [FAIL] Unallowed combination ctrl+alt+del was not rejected.")
            success = False
        except InvalidHotkeyError as e:
            print(f"  [PASS] Unallowed combination correctly rejected: {e}")

    except Exception as e:
        print(f"  [FAIL] Unexpected error during hotkey validation: {e}")
        success = False

    # 4. Mouse coordinates bounds
    print("\nTest 4: Mouse coordinates bounds validation...")
    try:
        # A. Valid coordinates
        policy.validate_coordinates(100, 200, 1920, 1080)
        print("  [PASS] Valid coordinates within bounds passed.")

        # B. Negative coordinate
        try:
            policy.validate_coordinates(-5, 100, 1920, 1080)
            print("  [FAIL] Negative coordinates were not rejected.")
            success = False
        except InvalidCoordinatesError as e:
            print(f"  [PASS] Negative coordinates correctly rejected: {e}")

        # C. Out-of-bounds X
        try:
            policy.validate_coordinates(1920, 500, 1920, 1080)
            print("  [FAIL] Out of bounds X coordinate was not rejected.")
            success = False
        except InvalidCoordinatesError as e:
            print(f"  [PASS] Out of bounds X coordinate correctly rejected: {e}")

    except Exception as e:
        print(f"  [FAIL] Unexpected error during coordinates validation: {e}")
        success = False

    # 5. Button validations
    print("\nTest 5: Mouse button validation...")
    try:
        # A. Valid buttons
        if policy.validate_button("left") == "left" and policy.validate_button(" RIGHT ") == "right":
            print("  [PASS] Valid mouse buttons validated successfully.")
        else:
            print("  [FAIL] Valid button returns incorrect name.")
            success = False

        # B. Invalid button
        try:
            policy.validate_button("middle")
            print("  [FAIL] Unsupported mouse button 'middle' was not rejected.")
            success = False
        except UnsupportedButtonError as e:
            print(f"  [PASS] Unsupported mouse button correctly rejected: {e}")

    except Exception as e:
        print(f"  [FAIL] Unexpected error during button validation: {e}")
        success = False

    print("\n==========================================================")
    if success:
        print("DIAGNOSTICS STATUS: PASS")
    else:
        print("DIAGNOSTICS STATUS: FAIL")
    print("==========================================================")
    return success


if __name__ == "__main__":
    ok = run_diagnostics()
    sys.exit(0 if ok else 1)
