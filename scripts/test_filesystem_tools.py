"""Diagnostic script for filesystem capability tools using a temporary directory."""

import os
import sys
import shutil
import tempfile
from app.core.application import Application
from app.agent.models import ToolCall

def run_diagnostic():
    print("=== Filesystem Tools Diagnostic ===")
    
    # Initialize Application
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    executor = app.container.get("tool_executor")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary workspace: {temp_dir}")
    
    failures = 0

    try:
        # 1. Setup diagnostic filesystem structure
        # Create directories
        dir_b = os.path.join(temp_dir, "dir_b")
        dir_a = os.path.join(temp_dir, "dir_a")
        os.makedirs(dir_b)
        os.makedirs(dir_a)
        
        # Create files
        file_b = os.path.join(temp_dir, "file_b.txt")
        file_a = os.path.join(temp_dir, "file_a.txt")
        with open(file_b, "w", encoding="utf-8") as f:
            f.write("Line 1 of B\nLine 2 of B\nLine 3 of B")
        with open(file_a, "w", encoding="utf-8") as f:
            f.write("Line 1 of A")
            
        # Create nested file to test no recursion
        nested_file = os.path.join(dir_a, "nested.txt")
        with open(nested_file, "w", encoding="utf-8") as f:
            f.write("nested content")

        # 2. Test list_directory ordering and no recursion
        print("\n1. Testing list_directory structure & ordering...")
        tc_list = ToolCall(tool_name="list_directory", arguments={"path": temp_dir, "limit": 10})
        res_list = executor.execute(tc_list)
        if res_list.success:
            entries = res_list.output.get("entries", [])
            print(f"  Returned count: {res_list.output.get('returned_count')}")
            # Verify ordering: directories first alphabetically, then files alphabetically
            expected_order = [
                ("dir_a", "directory"),
                ("dir_b", "directory"),
                ("file_a.txt", "file"),
                ("file_b.txt", "file")
            ]
            actual_order = [(e["name"], e["type"]) for e in entries]
            if actual_order == expected_order:
                print("  [PASS] Deterministic sorting correct (directories first, then files alphabetically).")
            else:
                print(f"  [FAIL] Deterministic sorting incorrect. Expected: {expected_order}, Got: {actual_order}")
                failures += 1
                
            # Verify no recursion (subdir 'dir_a' is listed, but its contents 'nested.txt' are not listed)
            if not any(e["name"] == "nested.txt" for e in entries):
                print("  [PASS] Directory list is non-recursive.")
            else:
                print("  [FAIL] Directory list leaked sub-contents recursively.")
                failures += 1
        else:
            print(f"  [FAIL] list_directory failed: {res_list.error}")
            failures += 1

        # 3. Test read_text_file content & truncation
        print("\n2. Testing read_text_file content & character truncation limit...")
        tc_read1 = ToolCall(tool_name="read_text_file", arguments={"path": file_b, "max_characters": 11})
        res_read1 = executor.execute(tc_read1)
        if res_read1.success:
            content = res_read1.output.get("content")
            truncated = res_read1.output.get("truncated")
            if content == "Line 1 of B" and truncated is True:
                print("  [PASS] Content successfully read and truncated exactly at max_characters boundary.")
            else:
                print(f"  [FAIL] Content mismatch. Read: {content!r}, Truncated: {truncated}")
                failures += 1
        else:
            print(f"  [FAIL] read_text_file failed: {res_read1.error}")
            failures += 1

        # 4. Test unsupported extension rejection
        print("\n3. Testing read_text_file unsupported extension rejection...")
        invalid_ext_file = os.path.join(temp_dir, "document.pdf")
        with open(invalid_ext_file, "w") as f:
            f.write("content")
        tc_read2 = ToolCall(tool_name="read_text_file", arguments={"path": invalid_ext_file})
        res_read2 = executor.execute(tc_read2)
        if not res_read2.success and "Unsupported file extension" in res_read2.error:
            print("  [PASS] Successfully rejected unsupported file extension (.pdf).")
        else:
            print(f"  [FAIL] Failed to block unsupported extension. Status: {res_read2.success}, Error: {res_read2.error}")
            failures += 1

        # 5. Test sensitive file rejection
        print("\n4. Testing sensitive credentials file rejection (.env)...")
        env_file = os.path.join(temp_dir, ".env")
        with open(env_file, "w") as f:
            f.write("DATABASE_URL=postgres://secret")
        tc_read3 = ToolCall(tool_name="read_text_file", arguments={"path": env_file})
        res_read3 = executor.execute(tc_read3)
        if not res_read3.success and "Access to sensitive file blocked" in res_read3.error:
            print("  [PASS] Successfully blocked sensitive credentials file (.env).")
        else:
            print(f"  [FAIL] Failed to block credentials file. Status: {res_read3.success}, Error: {res_read3.error}")
            failures += 1

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary workspace: {temp_dir}")

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
