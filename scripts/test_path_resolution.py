#!/usr/bin/env python3
"""Diagnostic script to verify Path Resolution logic and OS user folder mapping."""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver

def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def test_path_resolution():
    safe_print("=== Testing Dynamically Resolved OS Shell Folders ===")
    policy = FilesystemPolicy()
    resolver = FilesystemResolver(policy)
    
    supported_locations = [
        "desktop",
        "documents",
        "downloads",
        "home",
        "pictures",
        "videos",
        "music",
        "temp",
        "workspace",
    ]
    
    # 1. Verify every location is registered and resolves to an absolute path
    for loc in supported_locations:
        path = policy.get_root_path(loc)
        if not path:
            safe_print(f"FAIL: {loc} was not registered in policy.")
            sys.exit(1)
        if not path.is_absolute():
            safe_print(f"FAIL: {loc} path is not absolute: {path}")
            sys.exit(1)
        safe_print(f"PASS: {loc} resolved to: {path}")

    # 2. Verify username is never hardcoded
    # Path should not contain literal "<YourUser>" template or similar dummy values
    for loc in supported_locations:
        path_str = str(policy.get_root_path(loc))
        if "<" in path_str or ">" in path_str:
            safe_print(f"FAIL: {loc} contains dummy placeholder angle brackets: {path_str}")
            sys.exit(1)

    # 3. Verify absolute path resolution
    safe_print("\n=== Testing Absolute Path Resolution ===")
    temp_dir = tempfile.gettempdir()
    abs_path = os.path.join(temp_dir, "test_abs_file.txt")
    target = resolver.resolve("workspace", abs_path)
    safe_print(f"Resolved absolute path: {target.resolved_path}")
    if target.resolved_path != Path(abs_path).resolve():
        safe_print(f"FAIL: Absolute path resolved incorrectly. Expected {Path(abs_path).resolve()}, got {target.resolved_path}")
        sys.exit(1)
    safe_print("PASS: Absolute path resolved correctly.")

    # 4. Verify relative path resolution
    safe_print("\n=== Testing Relative Path Resolution ===")
    target = resolver.resolve("desktop", "Demo")
    expected = policy.get_root_path("desktop") / "Demo"
    if target.resolved_path != expected.resolve():
        safe_print(f"FAIL: Relative path resolved incorrectly. Expected {expected}, got {target.resolved_path}")
        sys.exit(1)
    safe_print("PASS: Relative path resolved correctly.")

    # 5. Verify virtual alias resolution (e.g. prefix alias in relative path)
    safe_print("\n=== Testing Virtual Alias Prefix Resolution ===")
    target = resolver.resolve("workspace", "Downloads/DemoFile.csv")
    expected = policy.get_root_path("downloads") / "DemoFile.csv"
    if target.resolved_path != expected.resolve():
        safe_print(f"FAIL: Virtual alias prefix resolved incorrectly. Expected {expected}, got {target.resolved_path}")
        sys.exit(1)
    safe_print("PASS: Virtual alias prefix resolved correctly.")

    safe_print("\n" + "=" * 60)
    safe_print("ALL PATH RESOLUTION DIAGNOSTICS PASSED SUCCESSFULLY!")
    safe_print("=" * 60)

if __name__ == "__main__":
    test_path_resolution()
