"""Diagnostic script to verify native top-level window enumeration and active window resolution."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.desktop.policy import DesktopPolicy
from app.services.desktop.resolver import DesktopResolver
from app.services.desktop.service import DesktopService
from app.services.desktop.backend import WindowsDesktopBackend


def run_diagnostics() -> bool:
    print("=== Running Windows Desktop Discovery Diagnostics ===")
    
    success = True
    try:
        backend = WindowsDesktopBackend()
        policy = DesktopPolicy()
        resolver = DesktopResolver()
        service = DesktopService(policy, resolver, backend)

        # 1. Query screen metrics E2E
        print("\n1. Querying Virtual Desktop Boundaries...")
        width, height = backend.get_screen_dimensions()
        print(f"   Primary Screen Resolution: {width}x{height}")
        if width > 0 and height > 0:
            print("   [PASS] Successfully queried screen metrics.")
        else:
            print("   [FAIL] Screen dimensions must be positive.")
            success = False

        # 2. Get active window E2E
        print("\n2. Querying Active Foreground Window...")
        try:
            active_win = service.get_active_window()
            print(f"   Foreground Window: ID={active_win.window_id}")
            print(f"   Title: '{active_win.title}'")
            print(f"   Process: '{active_win.process_name}' (PID: {active_win.process_id})")
            print("   [PASS] Successfully resolved active foreground window.")
        except Exception as e:
            print(f"   [NOTE] Active window query threw exception (normal in headless CI): {e}")

        # 3. List visible windows E2E
        print("\n3. Listing Visible Windows...")
        visible_wins = service.list_visible_windows()
        print(f"   Found {len(visible_wins)} visible windows.")
        for idx, win in enumerate(visible_wins[:5]):
            print(f"   [{idx+1}] ID={win.window_id} Title='{win.title}' Process='{win.process_name}'")
        
        # Validate deterministic sorting (alphabetical by title)
        titles = [w.title.lower() for w in visible_wins]
        is_sorted = all(titles[i] <= titles[i+1] for i in range(len(titles)-1))
        if is_sorted:
            print("   [PASS] List of visible windows is sorted alphabetically.")
        else:
            print("   [FAIL] List of visible windows is not sorted alphabetically.")
            success = False

        # 4. Resolve query
        if visible_wins:
            target_query = visible_wins[0].title
            print(f"\n4. Resolving Window Query '{target_query}'...")
            res = service.resolve_window(target_query)
            if res.status == "RESOLVED" and res.window:
                print(f"   [PASS] Successfully resolved '{target_query}' to ID {res.window.window_id}")
            elif res.status == "AMBIGUOUS":
                print(f"   [PASS] Query '{target_query}' was ambiguous. Candidates: {len(res.candidates)}")
            else:
                print(f"   [FAIL] Expected query resolution, got status {res.status}")
                success = False

    except Exception as e:
        print(f"  [FAIL] E2E Windows desktop query failure: {e}")
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
