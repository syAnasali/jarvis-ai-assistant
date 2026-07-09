"""Diagnostic script to verify filesystem policy constraints and path resolution."""

import os
import shutil
import tempfile
import sys
from pathlib import Path

from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver
from app.services.filesystem.service import FilesystemService
from app.core.exceptions import (
    InvalidRootError,
    InvalidPathError,
    PathEscapeError,
    UnsupportedPathError,
)


def run_diagnostics() -> bool:
    print("=== Running Filesystem Policy & Security Diagnostics ===")
    
    # 1. Setup isolated temporary roots
    temp_dir = Path(tempfile.mkdtemp())
    custom_roots = {
        "desktop": temp_dir / "Desktop",
        "documents": temp_dir / "Documents",
        "downloads": temp_dir / "Downloads",
        "workspace": temp_dir / "Workspace",
    }
    for p in custom_roots.values():
        p.mkdir(parents=True, exist_ok=True)

    success = True
    try:
        policy = FilesystemPolicy(custom_roots=custom_roots)
        resolver = FilesystemResolver(policy)
        service = FilesystemService(policy, resolver)

        # A. Valid nested resolution
        print("\nTest A: Valid nested resolution...")
        target = resolver.resolve("desktop", "invoices/2026/notes.txt")
        expected_path = custom_roots["desktop"] / "invoices/2026/notes.txt"
        if target.resolved_path.resolve() == expected_path.resolve() and target.exists is False:
            print("  [PASS] Valid nested resolution succeeded.")
        else:
            print(f"  [FAIL] Path mismatch. Got {target.resolved_path}, expected {expected_path}")
            success = False

        # B. Absolute path rejection
        print("\nTest B: Absolute path rejection...")
        try:
            resolver.resolve("desktop", "/absolute/path/file.txt")
            print("  [FAIL] Absolute path was not rejected.")
            success = False
        except InvalidPathError as e:
            print(f"  [PASS] Absolute path correctly rejected: {e}")

        # C. Drive path rejection
        print("\nTest C: Drive path rejection...")
        try:
            resolver.resolve("desktop", "C:\\windows\\system32")
            print("  [FAIL] Drive-qualified path was not rejected.")
            success = False
        except InvalidPathError as e:
            print(f"  [PASS] Drive-qualified path correctly rejected: {e}")

        # D. UNC path rejection
        print("\nTest D: UNC path rejection...")
        try:
            resolver.resolve("desktop", "\\\\server\\share\\file.txt")
            print("  [FAIL] UNC path was not rejected.")
            success = False
        except UnsupportedPathError as e:
            print(f"  [PASS] UNC path correctly rejected: {e}")

        # E. Traversal escape rejection
        print("\nTest E: Traversal escape rejection...")
        try:
            resolver.resolve("desktop", "invoices/../../../outside.txt")
            print("  [FAIL] Directory traversal escape was not rejected.")
            success = False
        except PathEscapeError as e:
            print(f"  [PASS] Directory traversal escape correctly rejected: {e}")

        # F. Root deletion protection
        print("\nTest F: Root deletion protection...")
        try:
            service.delete_path("desktop", "")
            print("  [FAIL] Root deletion was not blocked.")
            success = False
        except InvalidPathError as e:
            print(f"  [PASS] Root deletion correctly blocked: {e}")

    finally:
        # Clean up diagnostic data
        shutil.rmtree(temp_dir)

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
