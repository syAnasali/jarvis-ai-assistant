"""Diagnostic script to verify filesystem CRUD actions."""

import os
import shutil
import tempfile
import sys
from pathlib import Path

from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver
from app.services.filesystem.service import FilesystemService


def run_diagnostics() -> bool:
    print("=== Running Filesystem Actions Diagnostics ===")
    
    # Setup isolated temporary roots
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

        # 1. Create directory
        print("\n1. Create directory...")
        service.create_directory("desktop", "notes")
        dir_path = custom_roots["desktop"] / "notes"
        if dir_path.exists() and dir_path.is_dir():
            print("  [PASS] create_directory succeeded.")
        else:
            print("  [FAIL] create_directory failed.")
            success = False

        # 2. Write UTF-8 text
        print("\n2. Write UTF-8 text file...")
        service.write_text_file("desktop", "notes/todo.txt", "Buy milk. 😊")
        file_path = dir_path / "todo.txt"
        if file_path.exists() and file_path.read_text(encoding="utf-8") == "Buy milk. 😊":
            print("  [PASS] write_text_file succeeded.")
        else:
            print("  [FAIL] write_text_file failed.")
            success = False

        # 3. Inspect file
        print("\n3. Inspect file...")
        target = service.inspect_path("desktop", "notes/todo.txt")
        if target.exists and target.entry_type == "FILE":
            print(f"  [PASS] inspect_path metadata: root={target.root}, rel={target.relative_path}, type={target.entry_type}")
        else:
            print("  [FAIL] inspect_path failed.")
            success = False

        # 4. List directory
        print("\n4. List directory...")
        list_res = service.list_directory("desktop", "notes")
        entries = list_res["entries"]
        if len(entries) == 1 and entries[0]["name"] == "todo.txt" and entries[0]["entry_type"] == "FILE":
            print(f"  [PASS] list_directory entries: {entries}")
        else:
            print(f"  [FAIL] list_directory failed. Entries: {entries}")
            success = False

        # 5. Move file
        print("\n5. Move file...")
        service.move_path("desktop", "notes/todo.txt", "documents", "moved_todo.txt")
        src_path = custom_roots["desktop"] / "notes/todo.txt"
        dest_path = custom_roots["documents"] / "moved_todo.txt"
        if not src_path.exists() and dest_path.exists() and dest_path.read_text(encoding="utf-8") == "Buy milk. 😊":
            print("  [PASS] move_path succeeded.")
        else:
            print("  [FAIL] move_path failed.")
            success = False

        # 6. Delete file
        print("\n6. Delete file...")
        service.delete_path("documents", "moved_todo.txt")
        if not dest_path.exists():
            print("  [PASS] delete_path (file) succeeded.")
        else:
            print("  [FAIL] delete_path (file) failed.")
            success = False

        # 7. Delete directory
        print("\n7. Delete directory...")
        service.delete_path("desktop", "notes")
        if not dir_path.exists():
            print("  [PASS] delete_path (directory) succeeded.")
        else:
            print("  [FAIL] delete_path (directory) failed.")
            success = False

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
