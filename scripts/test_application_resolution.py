"""Diagnostic script for Windows application resolution."""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.application import Application
from app.services.applications.resolver import ApplicationResolver


def run_diagnostic():
    print("=== Application Resolution Diagnostic ===")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"FAILED: Application initialization failed: {e}")
        sys.exit(1)

    resolver = ApplicationResolver()
    
    # We test local resolution for Notepad, Calculator, VS Code, Ollama
    queries = [
        "Notepad",
        "notepad",
        "Calculator",
        "calc",
        "Visual Studio Code",
        "vscode",
        "Ollama"
    ]
    
    failures = 0
    
    for query in queries:
        resolution = resolver.resolve(query)
        print(f"\nQuery: '{query}'")
        print(f"  Status: {resolution.status}")
        print(f"  Match Type: {resolution.match_type}")
        
        if resolution.status == "RESOLVED":
            print(f"  [PASS] Resolved Name: {resolution.application.name}")
            print(f"         ID: {resolution.application.application_id}")
        elif resolution.status == "AMBIGUOUS":
            print(f"  [PASS] Ambiguous (found {len(resolution.candidates)} candidates):")
            for c in resolution.candidates:
                print(f"         - {c.name} (ID: {c.application_id})")
        else:
            # NOT_FOUND is acceptable for optional third-party apps like VS Code or Ollama,
            # but built-ins (Notepad, Calculator) should be found.
            is_built_in = query.lower() in ("notepad", "calculator", "calc")
            if is_built_in:
                print("  [FAIL] Built-in application not found.")
                failures += 1
            else:
                print("  [INFO] Optional application not found (this is normal if not installed).")

    print("\n-------------------------------------------")
    if failures == 0:
        print("DIAGNOSTIC STATUS: PASS")
    else:
        print(f"DIAGNOSTIC STATUS: FAIL ({failures} failures)")
        sys.exit(1)


if __name__ == "__main__":
    run_diagnostic()
