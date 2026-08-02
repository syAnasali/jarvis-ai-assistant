#!/usr/bin/env python3
"""Main runner script for the Jarvis Production Regression Suite.

Discovers and executes all test scripts under scripts/regression/ and prints a summary.
"""

import sys
import os
import time
import importlib.util
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))


def run_all_regressions():
    print("=" * 80)
    print("      JARVIS AI ASSISTANT - PRODUCTION REGRESSION SUITE")
    print("=" * 80)

    regression_dir = Path(__file__).parent.resolve()
    
    # Locate all test_*.py files in scripts/regression except run_all.py
    test_files = sorted([
        f for f in regression_dir.glob("test_*.py")
        if f.name != "run_all.py"
    ])
    
    results = []
    total_start_time = time.perf_counter()
    
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    
    for f in test_files:
        print(f"Executing {f.name}...", end="", flush=True)
        
        # Load and run regression module
        spec = importlib.util.spec_from_file_location(f.stem, str(f))
        module = importlib.util.module_from_spec(spec)
        
        step_start = time.perf_counter()
        try:
            spec.loader.exec_module(module)
            if hasattr(module, "run_regression"):
                res = module.run_regression()
            else:
                res = {
                    "name": f.name,
                    "status": "FAIL",
                    "duration": time.perf_counter() - step_start,
                    "reason": "Missing run_regression() function entry point."
                }
        except Exception as e:
            res = {
                "name": f.name,
                "status": "FAIL",
                "duration": time.perf_counter() - step_start,
                "reason": f"Execution crash: {e}"
            }
            
        # Update counts
        status = res.get("status", "FAIL")
        if status == "PASS":
            passed_count += 1
            print(" [PASS]")
        elif status == "SKIP":
            skipped_count += 1
            print(" [SKIP]")
        else:
            failed_count += 1
            print(" [FAIL]")
            
        results.append(res)

    total_runtime = time.perf_counter() - total_start_time
    
    print("\n" + "=" * 80)
    print(f"{'TEST NAME':<25} | {'STATUS':<6} | {'DURATION':<10} | {'REASON / LOG'}")
    print("-" * 80)
    
    for r in results:
        duration_str = f"{r['duration']:.4f}s"
        print(f"{r['name']:<25} | {r['status']:<6} | {duration_str:<10} | {r['reason']}")
        
    print("=" * 80)
    print("                               FINAL REPORT")
    print("=" * 80)
    print(f"Total Tests Run: {len(results)}")
    print(f"Passed:          {passed_count}")
    print(f"Failed:          {failed_count}")
    print(f"Skipped:         {skipped_count}")
    print(f"Total Runtime:   {total_runtime:.2f} seconds")
    print("=" * 80)

    # Return exit code based on failures
    if failed_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    run_all_regressions()
